"""
Email service — sends transactional emails via SMTP.

Currently used for password reset emails only (Q6: no external notifications).
Uses aiosmtplib for non-blocking async SMTP so the event loop is not blocked.

Design decisions:
- SMTP credentials are from settings (configurable per environment).
- HTML + plain text multipart emails for maximum compatibility.
- Connection is created per-send (not pooled) because email volume is low
  and SMTP connections are stateful/fragile across long idle periods.
- Errors are caught and logged — email failure should NOT crash the auth flow
  (the token is already created; user can re-request).
"""
from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    """Handles all outbound email delivery."""

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str,
    ) -> bool:
        """
        Send a password reset link to the user's connected Gmail address.

        Args:
            to_email: Recipient email address (from gmail_connections.gmail_email).
            username: User's username (for personalisation).
            reset_token: Raw reset token to embed in the link.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

        subject = f"Reset your {settings.app_name} password"

        plain_text = (
            f"Hi {username},\n\n"
            f"You requested a password reset for your {settings.app_name} account.\n\n"
            f"Click the link below to reset your password:\n{reset_url}\n\n"
            f"This link expires in {settings.password_reset_token_expire_minutes} minutes.\n\n"
            f"If you didn't request this, please ignore this email.\n\n"
            f"The {settings.app_name} Team"
        )

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             background: #f8fafc; margin: 0; padding: 40px 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff;
              border-radius: 12px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,.1);">
    <h1 style="font-size: 22px; font-weight: 700; color: #1e293b; margin: 0 0 8px;">
      Password Reset
    </h1>
    <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
      Hi <strong>{username}</strong>, we received a request to reset your
      <strong>{settings.app_name}</strong> password.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; background: #6366f1; color: #ffffff;
              font-weight: 600; font-size: 15px; text-decoration: none;
              padding: 12px 28px; border-radius: 8px; margin-bottom: 24px;">
      Reset Password
    </a>
    <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0 0 8px;">
      This link expires in
      <strong>{settings.password_reset_token_expire_minutes} minutes</strong>.
    </p>
    <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0;">
      If you didn't request this, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
    <p style="color: #cbd5e1; font-size: 12px; margin: 0;">
      {settings.app_name} · Sent to {to_email}
    </p>
  </div>
</body>
</html>
"""

        return await self._send(
            to_email=to_email,
            subject=subject,
            plain_text=plain_text,
            html_content=html_content,
        )

    async def _send(
        self,
        to_email: str,
        subject: str,
        plain_text: str,
        html_content: str,
    ) -> bool:
        """
        Internal method: build and dispatch a MIME multipart email.

        Raises nothing — all errors are caught and logged.
        Returns True on success, False on failure.
        """
        if not settings.smtp_host or not settings.smtp_username:
            logger.warning(
                "smtp_not_configured",
                hint="Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD in .env",
            )
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = to_email

        message.attach(MIMEText(plain_text, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=False,
                start_tls=settings.smtp_use_tls,
            )
            logger.info("email_sent", to=to_email, subject=subject)
            return True
        except aiosmtplib.SMTPException as exc:
            logger.error(
                "smtp_error",
                to=to_email,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return False
        except Exception as exc:
            logger.error(
                "email_send_unexpected_error",
                to=to_email,
                error=str(exc),
            )
            return False


# Singleton
email_service = EmailService()
