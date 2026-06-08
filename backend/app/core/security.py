"""
Security utilities: password hashing, JWT, AES-256-GCM encryption.

This module is the single source of all cryptographic operations.
No other module should implement its own hashing or encryption logic.

Design decisions:
- bcrypt cost factor 12: OWASP recommended minimum for 2024.
- JWT HS256 with a 64+ char secret: sufficient for single-server deployment.
  RS256 should be considered if token verification needs to be done by
  multiple services without sharing the secret.
- AES-256-GCM for Gmail tokens: authenticated encryption (prevents
  ciphertext tampering). A random 96-bit nonce per encryption ensures
  no two ciphertexts are identical even for the same plaintext.
- SHA-256 (not bcrypt) for password reset tokens: reset tokens are
  high-entropy (256-bit) random values, so the pre-image resistance of
  SHA-256 is sufficient without bcrypt's slowness.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import structlog
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.config import settings

logger = structlog.get_logger(__name__)

# ── Password Hashing ───────────────────────────────────────────────────────────
# We use the `bcrypt` library directly (not passlib) because passlib is
# effectively unmaintained and has a known crash with bcrypt>=4.0 where its
# internal self-test tries to verify a >72-byte secret and raises ValueError.
_BCRYPT_ROUNDS: int = 12


def hash_password(password: str) -> str:
    """Return the bcrypt hash of a plaintext password."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# ── JWT ────────────────────────────────────────────────────────────────────────
def create_access_token(
    subject: str | UUID,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: User ID to embed as the 'sub' claim.
        extra_claims: Optional additional claims (e.g., username).
        expires_delta: Override the default expiry.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Raises:
        JWTError: If the token is invalid, expired, or tampered.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


# ── Refresh Tokens ─────────────────────────────────────────────────────────────
def create_refresh_token() -> str:
    """
    Generate a cryptographically secure opaque refresh token.

    Returns a 64-byte URL-safe base64 string (512 bits of entropy).
    The raw token is delivered to the client via HttpOnly cookie.
    Only its bcrypt hash is stored in the database.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """
    Return the SHA-256 hash of a refresh token for database storage.

    SHA-256 is used instead of bcrypt because refresh tokens are generated
    by secrets.token_urlsafe(64), producing ~86-character strings that exceed
    bcrypt's 72-byte input limit. Since refresh tokens are already high-entropy
    (512 bits), SHA-256's pre-image resistance is sufficient — an attacker with
    the DB cannot feasibly reverse the hash to obtain a valid token.
    """
    return _sha256(token)


def verify_refresh_token(token: str, hashed: str) -> bool:
    """Verify a raw refresh token against its stored SHA-256 hash."""
    return secrets.compare_digest(_sha256(token), hashed)


# ── Password Reset Tokens ──────────────────────────────────────────────────────
def create_password_reset_token() -> tuple[str, str]:
    """
    Generate a single-use password reset token.

    Returns:
        (raw_token, sha256_hash): raw_token is sent via email;
        sha256_hash is stored in the database.
    """
    raw = secrets.token_urlsafe(32)
    token_hash = _sha256(raw)
    return raw, token_hash


def hash_reset_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of a raw password reset token."""
    return _sha256(raw_token)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ── AES-256-GCM Encryption (Gmail Tokens) ─────────────────────────────────────
def _get_aes_key() -> bytes:
    """Decode and validate the AES-256-GCM encryption key from settings."""
    try:
        key_bytes = b64decode(settings.encryption_key + "==")
        # Accept both 32-byte (AES-256) keys
        if len(key_bytes) < 32:
            raise ValueError(
                f"Encryption key must be ≥32 bytes; got {len(key_bytes)}"
            )
        return key_bytes[:32]
    except Exception as exc:
        logger.critical("invalid_encryption_key", error=str(exc))
        raise RuntimeError("Server misconfiguration: invalid ENCRYPTION_KEY") from exc


def encrypt_text(plaintext: str) -> str:
    """
    Encrypt a plaintext string using AES-256-GCM.

    Output format: base64(nonce[12] + ciphertext+tag)

    A fresh 96-bit nonce is generated for every call — this is critical
    for GCM security. Reusing a nonce with the same key is catastrophic.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)                          # 96-bit nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_text(encrypted_text: str) -> str:
    """
    Decrypt a string encrypted by encrypt_text.

    Raises:
        cryptography.exceptions.InvalidTag: If the ciphertext has been tampered.
        ValueError: If the payload is malformed.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    try:
        combined = b64decode(encrypted_text.encode("utf-8"))
        nonce, ciphertext = combined[:12], combined[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as exc:
        logger.error("decrypt_failed", error=type(exc).__name__)
        raise ValueError("Decryption failed — data may be corrupted or key mismatch") from exc
