"""
Gmail Client for fetching emails securely.
Handles token refresh, pagination, rate-limiting, and exponential backoff.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

import httpx
import structlog
from httpx import HTTPStatusError

from app.config import settings
from app.core.security import decrypt_text

logger = structlog.get_logger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_MESSAGES_URL = "https://www.googleapis.com/gmail/v1/users/me/messages"


class GmailAPIError(Exception):
    pass


class GmailClient:
    """Client for securely interacting with Gmail API."""

    def __init__(self, encrypted_refresh_token: str):
        self.refresh_token = decrypt_text(encrypted_refresh_token)
        self.access_token: str | None = None
        self.access_token_expires_at: datetime | None = None
        # Use a single httpx client session for connection pooling
        self.client = httpx.AsyncClient(timeout=15.0)

    async def _refresh_access_token(self) -> str:
        """Fetch a new access token using the refresh token."""
        now = datetime.now(timezone.utc)
        if self.access_token and self.access_token_expires_at and self.access_token_expires_at > now:
            return self.access_token

        res = await self.client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if res.status_code != 200:
            logger.error("gmail_token_refresh_failed", response=res.text)
            raise GmailAPIError("Failed to refresh Gmail access token.")

        data = res.json()
        self.access_token = data["access_token"]
        # Subtract 1 minute for safe buffer
        import datetime as dt
        self.access_token_expires_at = now + dt.timedelta(seconds=data.get("expires_in", 3599) - 60)
        return self.access_token

    async def _request_with_backoff(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute an HTTP request with exponential backoff for rate limits."""
        max_retries = 5
        base_delay = 1.0

        for attempt in range(max_retries):
            token = await self._refresh_access_token()
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers

            res = await self.client.request(method, url, **kwargs)

            # 429 Too Many Requests or 5xx Server Errors
            if res.status_code in (429, 500, 502, 503, 504):
                if attempt == max_retries - 1:
                    raise GmailAPIError(f"Gmail API max retries exceeded: {res.status_code} - {res.text}")
                
                delay = base_delay * (2 ** attempt)
                logger.warning("gmail_api_rate_limited", attempt=attempt, delay=delay, status=res.status_code)
                await asyncio.sleep(delay)
                continue
                
            res.raise_for_status()
            return res
            
        raise GmailAPIError("Request failed unexpectedly.")

    async def list_message_ids(
        self, after_date: datetime, query: str = ""
    ) -> AsyncGenerator[list[dict], None]:
        """
        Yields batches (pages) of message IDs matching the query.
        """
        # Convert date to Unix timestamp seconds for the `after:` query
        timestamp = int(after_date.timestamp())
        q = f"after:{timestamp}"
        if query:
            q += f" {query}"

        page_token = None
        
        while True:
            params = {"q": q, "maxResults": 500}
            if page_token:
                params["pageToken"] = page_token

            res = await self._request_with_backoff("GET", GMAIL_MESSAGES_URL, params=params)
            data = res.json()

            messages = data.get("messages", [])
            if messages:
                yield messages

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    async def get_message_metadata(self, msg_id: str) -> dict:
        """
        Fetch email metadata and snippet. (format=metadata prevents full body fetch)
        """
        url = f"{GMAIL_MESSAGES_URL}/{msg_id}"
        # Fetching only essential headers to save bandwidth
        headers_to_fetch = ["Subject", "From", "To", "Date"]
        params = {
            "format": "metadata",
            "metadataHeaders": headers_to_fetch,
        }
        
        res = await self._request_with_backoff("GET", url, params=params)
        return res.json()

    async def fetch_full_body(self, msg_id: str) -> str | None:
        """
        Fetch the full raw email body.
        Used temporarily during the parsing pipeline and immediately discarded.
        """
        url = f"{GMAIL_MESSAGES_URL}/{msg_id}"
        params = {"format": "raw"}
        res = await self._request_with_backoff("GET", url, params=params)
        data = res.json()
        
        raw_data = data.get("raw")
        if not raw_data:
            return None
            
        import base64
        import email
        
        try:
            # Gmail uses urlsafe base64
            msg_bytes = base64.urlsafe_b64decode(raw_data)
            msg = email.message_from_bytes(msg_bytes)
            
            # Extract plain text or html body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type in ("text/plain", "text/html") and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            # Prefer plain text, but append html if needed or just return text
                            text = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                            if content_type == "text/plain":
                                return text # Return early if plain text is found
                            body += text
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
            
            return body
        except Exception as e:
            logger.error("failed_to_decode_raw_email", msg_id=msg_id, error=str(e))
            return None

    async def close(self) -> None:
        """Close the internal HTTP client."""
        await self.client.aclose()
