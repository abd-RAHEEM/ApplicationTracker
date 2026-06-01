"""Email repository."""
from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email
from app.repositories.base_repository import BaseRepository


class EmailRepository(BaseRepository[Email]):
    """Data access layer for emails."""

    def __init__(self) -> None:
        super().__init__(Email)

    async def bulk_upsert_emails(
        self, session: AsyncSession, user_id: UUID, email_dicts: Iterable[dict]
    ) -> int:
        """
        Efficiently bulk insert emails. Updates fields if the email already exists
        based on the user_id and gmail_msg_id unique constraint.
        """
        if not email_dicts:
            return 0

        # Inject user_id into all dicts
        values_to_insert = []
        for e in email_dicts:
            val = dict(e)
            val["user_id"] = user_id
            values_to_insert.append(val)

        stmt = insert(Email).values(values_to_insert)

        # On conflict, do update (upsert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "gmail_msg_id"],
            set_={
                "gmail_thread_id": stmt.excluded.gmail_thread_id,
                "gmail_label_ids": stmt.excluded.gmail_label_ids,
                "subject": stmt.excluded.subject,
                "sender": stmt.excluded.sender,
                "recipient": stmt.excluded.recipient,
                "date": stmt.excluded.date,
                "snippet": stmt.excluded.snippet,
            },
        ).returning(Email.id)

        result = await session.execute(stmt)
        await session.flush()
        return len(result.all())


email_repository = EmailRepository()
