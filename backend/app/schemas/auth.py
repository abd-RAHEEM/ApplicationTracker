"""
Pydantic v2 schemas for authentication endpoints.

Covers: register, login, logout, token refresh, password reset request,
password reset confirm.

Validation rules:
- Username: 3–100 chars, alphanumeric + underscore only.
- Password: min 8 chars, at least one uppercase, lowercase, digit, special char.
- Passwords must match on registration.
"""
from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import AppBaseModel

# Password strength regex
_PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#^()+={}\[\]|\\:;\"'<>,.?/~`])"
    r".{8,}$"
)

# Username regex: alphanumeric + underscore, 3–100 chars
_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,100}$")


# ── Register ───────────────────────────────────────────────────────────────────
class RegisterRequest(AppBaseModel):
    """Payload for POST /auth/register."""

    full_name: str = Field(
        min_length=2,
        max_length=255,
        description="User's display name",
        examples=["Jane Doe"],
    )
    username: str = Field(
        min_length=3,
        max_length=100,
        description="Unique login handle (alphanumeric + underscore)",
        examples=["janedoe"],
    )
    password: str = Field(
        max_length=128,
        description="Strong password (uppercase, lowercase, digit, special char)",
    )
    confirm_password: str = Field(
        max_length=128,
        description="Must match password exactly",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_REGEX.match(v):
            raise ValueError(
                "Username may only contain letters, numbers, and underscores (3–100 chars)"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not _PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters and include an uppercase letter, "
                "lowercase letter, number, and special character"
            )
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# ── Login ──────────────────────────────────────────────────────────────────────
class LoginRequest(AppBaseModel):
    """Payload for POST /auth/login."""

    username: str = Field(min_length=3, max_length=100, examples=["janedoe"])
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalise_username(cls, v: str) -> str:
        return v.lower().strip()


# ── Password Reset — Request ───────────────────────────────────────────────────
class PasswordResetRequestSchema(AppBaseModel):
    """Payload for POST /auth/forgot-password."""

    username: str = Field(
        min_length=3,
        max_length=100,
        description="The username to send the reset link for",
    )

    @field_validator("username")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.lower().strip()


# ── Password Reset — Confirm ───────────────────────────────────────────────────
class PasswordResetConfirmSchema(AppBaseModel):
    """Payload for POST /auth/reset-password."""

    token: str = Field(
        min_length=10,
        description="Reset token received via email",
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New strong password",
    )
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not _PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must be at least 8 characters and include an uppercase letter, "
                "lowercase letter, number, and special character"
            )
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordResetConfirmSchema":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


# ── Responses ──────────────────────────────────────────────────────────────────
class UserAuthResponse(AppBaseModel):
    """Minimal user info returned after register/login."""

    id: UUID
    username: str
    full_name: str
    gmail_connected: bool = False
    initial_import_done: bool = False
    is_onboarding_completed: bool = False


class LoginResponse(AppBaseModel):
    """Data payload for a successful login response."""

    user: UserAuthResponse


class RegisterResponse(AppBaseModel):
    """Data payload for a successful registration response."""

    id: UUID
    username: str
    full_name: str
    created_at: datetime


class TokenRefreshResponse(AppBaseModel):
    """Returned after a successful token refresh (cookie is also set)."""

    message: str = "Token refreshed successfully"


class MessageResponse(AppBaseModel):
    """Generic message-only response (logout, password reset email sent, etc.)."""

    message: str
