"""
Sync orchestration logic.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

import structlog
from dateutil.parser import parse as parse_date

from app.core.gmail_client import GmailClient
from app.core.redis import publish_sse_event
from app.db.session import async_session_maker
from app.models.sync_log import SyncStatus, SyncType
from app.repositories.email_repository import email_repository
from app.repositories.gmail_repository import gmail_repository
from app.repositories.sync_log_repository import sync_log_repository

logger = structlog.get_logger(__name__)

# Max concurrent requests to Gmail API per user sync
MAX_CONCURRENT_REQUESTS = 10


def _parse_headers(payload: dict) -> dict:
    """Extracts Subject, From, To, and Date from Gmail API payload headers."""
    headers = payload.get("headers", [])
    result = {"subject": None, "sender": None, "recipient": None, "date": None}
    
    for h in headers:
        name = h.get("name", "").lower()
        val = h.get("value")
        if name == "subject":
            result["subject"] = val
        elif name == "from":
            result["sender"] = val
        elif name == "to":
            result["recipient"] = val
        elif name == "date":
            try:
                result["date"] = parse_date(val)
            except Exception:
                pass
    return result


async def run_sync_for_user(user_id: UUID, task_id: str | None = None) -> None:
    """
    Executes the email sync for a user.
    Uses async sessions explicitly since it runs in a Celery background task.
    """
    async with async_session_maker() as session:
        conn = await gmail_repository.get_connection(session, user_id)
        if not conn:
            logger.error("sync_aborted_no_connection", user_id=str(user_id))
            return

        sync_type = SyncType.INCREMENTAL if conn.initial_import_done else SyncType.INITIAL_IMPORT
        log = await sync_log_repository.start_sync(session, user_id, sync_type, task_id)
        log_id = log.id

        # For the initial import, ALWAYS use the user-configured import_from date
        # (the "last 6 months" window they chose at onboarding).
        # For incremental syncs, pick up from the last successful sync timestamp.
        # This prevents the common bug where a failed/partial initial import then
        # uses today's date on retry — missing all historical emails.
        if sync_type == SyncType.INITIAL_IMPORT:
            after_date = conn.initial_import_from
        else:
            after_date = conn.last_successful_sync_at or conn.initial_import_from

        if not after_date:
            # Fallback: 6 months ago if somehow initial_import_from is missing
            from datetime import timedelta
            after_date = datetime.now(timezone.utc) - timedelta(days=180)
            logger.warning("sync_missing_import_from_fallback", user_id=str(user_id))
            
        client = GmailClient(conn.encrypted_refresh_token)
        
        # Publish start event
        await publish_sse_event(str(user_id), json.dumps({"event": "sync_started"}))

        try:
            total_fetched = 0
            
            # Iterate through paginated message IDs
            async for messages_page in client.list_message_ids(after_date=after_date):
                page_emails = []
                
                # Semaphore to limit concurrent fetch requests to prevent API spam
                sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
                
                async def fetch_msg(msg_id: str):
                    async with sem:
                        return await client.get_message_metadata(msg_id)
                        
                fetch_tasks = [fetch_msg(m["id"]) for m in messages_page]
                msg_responses = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                
                for res in msg_responses:
                    if isinstance(res, Exception):
                        logger.error("gmail_message_fetch_error", error=str(res))
                        continue
                        
                    payload = res.get("payload", {})
                    headers = _parse_headers(payload)
                    
                    # Convert internalDate (epoch ms) to datetime
                    internal_date_ms = int(res.get("internalDate", 0))
                    internal_date = datetime.fromtimestamp(internal_date_ms / 1000.0, tz=timezone.utc)
                    
                    page_emails.append({
                        "gmail_msg_id": res["id"],
                        "gmail_thread_id": res["threadId"],
                        "gmail_internal_date": internal_date,
                        "gmail_label_ids": res.get("labelIds", []),
                        "snippet": res.get("snippet"),
                        "subject": headers["subject"],
                        "sender": headers["sender"],
                        "recipient": headers["recipient"],
                        "date": headers["date"],
                    })

                # Bulk upsert the fetched page
                if page_emails:
                    upserted = await email_repository.bulk_upsert_emails(session, user_id, page_emails)
                    total_fetched += upserted
                    
                    # Update progress in db and redis
                    await sync_log_repository.increment_progress(session, log_id, upserted)
                    await publish_sse_event(str(user_id), json.dumps({
                        "event": "page_processed",
                        "emails_processed": total_fetched
                    }))

            # Entire mailbox processed successfully
            now = datetime.now(timezone.utc)
            await gmail_repository.update_sync_timestamp(session, user_id, now)
            
            if not conn.initial_import_done:
                # Need to use an update statement to set initial_import_done
                from sqlalchemy import update
                from app.models.gmail_connection import GmailConnection
                await session.execute(
                    update(GmailConnection)
                    .where(GmailConnection.user_id == user_id)
                    .values(initial_import_done=True)
                )
                await session.flush()

            await sync_log_repository.finish_sync(session, log_id, SyncStatus.COMPLETED, total_fetched)
            await publish_sse_event(str(user_id), json.dumps({
                "event": "sync_completed",
                "emails_processed": total_fetched
            }))
            logger.info("sync_completed", user_id=str(user_id), fetched=total_fetched)
            
            # Trigger Parsing Phase
            await publish_sse_event(str(user_id), json.dumps({"event": "parsing_started"}))
            from app.services.parser_service import parser_service
            await parser_service.process_unparsed_emails(session, user_id)
            await publish_sse_event(str(user_id), json.dumps({"event": "parsing_completed"}))
            
            # Generate Analytics
            from app.worker.tasks import generate_analytics_task
            generate_analytics_task.delay(str(user_id))

        except Exception as e:
            logger.exception("sync_failed", user_id=str(user_id))
            await session.rollback() # rollback any pending uncommitted bulk upserts in this session
            await sync_log_repository.finish_sync(session, log_id, SyncStatus.FAILED, error_message=str(e))
            await publish_sse_event(str(user_id), json.dumps({
                "event": "sync_failed",
                "error": str(e)
            }))
        finally:
            await client.close()
