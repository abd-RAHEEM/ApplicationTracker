"""
Application configuration loaded from environment variables.

Uses Pydantic Settings for validation and type coercion.
All sensitive values are read from the environment — never hard-coded.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralised application settings.

    Values are loaded in priority order:
      1. Explicit environment variable
      2. .env file
      3. Default value defined here

    Rationale for Pydantic Settings:
    - Type coercion and validation at startup (fail fast).
    - Single source of truth — no scattered os.getenv() calls.
    - IDE auto-complete and mypy compatibility.

    Note on local development:
    - In local development (with React Strict Mode enabled), effects are run twice on mount,
      which can cause rapid successive requests to hit rate limits.
      To prevent this, override rate limits in .env or the shell environment:
      RATE_LIMIT_LOGIN="200/minute"
      RATE_LIMIT_REGISTER="100/minute"
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",             # Ignore unknown env vars gracefully
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "JobTracker"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Server ─────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins_raw: str | list[str] = Field(
        default=["http://localhost:3000"],
        validation_alias="allowed_origins",
    )

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = Field(
        description="Async PostgreSQL URL (postgresql+asyncpg://...)"
    )
    database_url_sync: str = Field(
        description="Sync PostgreSQL URL for Alembic (postgresql+psycopg://...)"
    )

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ────────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90)

    # ── AES-256-GCM Encryption ─────────────────────────────────────────────────
    encryption_key: str = Field(
        min_length=44,
        description="Base64-encoded 32-byte key for AES-256-GCM",
    )

    # ── Google OAuth ───────────────────────────────────────────────────────────
    # Required for Phase 2+. Set in .env — never default to empty in production.
    google_client_id: str = ""
    google_client_secret: str = ""
    # Must match the authorized redirect URI in Google Cloud Console exactly.
    # Development: http://localhost:8000/v1/gmail/callback
    google_redirect_uri: str = "http://localhost:8000/v1/gmail/callback"
    # OAuth state JWT expiry (seconds) — short-lived CSRF protection token.
    oauth_state_expire_seconds: int = Field(default=300, ge=60, le=600)

    # ── SMTP ───────────────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "JobTracker"
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    # ── Frontend ───────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    rate_limit_login: str = "30/minute"
    rate_limit_register: str = "15/minute"
    rate_limit_password_reset: str = "15/minute"
    rate_limit_sync: str = "5/minute"

    # ── Password Reset ─────────────────────────────────────────────────────────
    password_reset_token_expire_minutes: int = Field(default=15, ge=5, le=60)

    # ── Bin ────────────────────────────────────────────────────────────────────
    bin_retention_days: int = Field(default=15, ge=1, le=90)

    # ── Computed Properties ────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """True when running in the development environment."""
        return self.environment == "development"

    @property
    def access_token_expire_seconds(self) -> int:
        """Access token TTL in seconds (for cookie max_age)."""
        return self.access_token_expire_minutes * 60

    @property
    def refresh_token_expire_seconds(self) -> int:
        """Refresh token TTL in seconds (for cookie max_age)."""
        return self.refresh_token_expire_days * 86400

    @property
    def cookie_secure(self) -> bool:
        """
        Whether to set Secure flag on cookies.
        Only True in production (requires HTTPS).
        """
        return self.is_production

    # ── Validators ─────────────────────────────────────────────────────────────
    @field_validator("allowed_origins_raw", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS env var into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Automatically rewrite direct Supabase host to IPv4-compatible pooler host if needed."""
        if "db.exgxhodksfxgosdahziz.supabase.co" in v:
            v = v.replace(
                "db.exgxhodksfxgosdahziz.supabase.co",
                "aws-1-ap-southeast-2.pooler.supabase.com"
            )
            v = v.replace(
                "postgresql+asyncpg://postgres:",
                "postgresql+asyncpg://postgres.exgxhodksfxgosdahziz:"
            )
        return v

    @property
    def allowed_origins(self) -> list[str]:
        """Get the parsed list of allowed CORS origins."""
        if isinstance(self.allowed_origins_raw, str):
            return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]
        return self.allowed_origins_raw


@lru_cache
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    Using lru_cache means .env is read once at startup, not on every request.
    The cache is cleared between tests using get_settings.cache_clear().
    """
    return Settings()  # type: ignore[call-arg]


# Module-level convenience instance.
# Import this throughout the codebase: `from app.config import settings`
settings: Settings = get_settings()
