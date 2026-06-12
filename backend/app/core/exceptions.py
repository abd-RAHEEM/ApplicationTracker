"""
Custom exception classes and global FastAPI exception handlers.

Architecture:
  - AppException: base class for all domain exceptions.
  - Specific subclasses map to HTTP status codes for consistent API responses.
  - register_exception_handlers() attaches handlers to the FastAPI app.

Rationale for custom exceptions:
  Route handlers raise typed exceptions (e.g., raise NotFoundException(...))
  instead of HTTPExceptions. This keeps business logic decoupled from HTTP
  semantics and makes unit tests simpler (no need to import HTTPException).
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


# ── Base Exception ─────────────────────────────────────────────────────────────
class AppException(Exception):
    """Base class for all application exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.details = details or {}
        super().__init__(self.message)


# ── 400 Bad Request ────────────────────────────────────────────────────────────
class BadRequestException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    message = "Bad request"


class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


# ── 401 Unauthorized ───────────────────────────────────────────────────────────
class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"
    message = "Authentication required"


class InvalidCredentialsException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_CREDENTIALS"
    message = "Username or password is incorrect"


class TokenExpiredException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "TOKEN_EXPIRED"
    message = "Authentication token has expired"


class InvalidTokenException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "INVALID_TOKEN"
    message = "Authentication token is invalid"


class SessionRevokedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "SESSION_REVOKED"
    message = "Session has been revoked — please log in again"


# ── 403 Forbidden ──────────────────────────────────────────────────────────────
class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


# ── 404 Not Found ──────────────────────────────────────────────────────────────
class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "Resource not found"


# ── 409 Conflict ───────────────────────────────────────────────────────────────
class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "Resource already exists"


class UsernameTakenException(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "USERNAME_TAKEN"
    message = "This username is already registered"


# ── 422 Unprocessable ─────────────────────────────────────────────────────────
class WeakPasswordException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "WEAK_PASSWORD"
    message = (
        "Password must be at least 8 characters and include an uppercase letter, "
        "lowercase letter, number, and special character"
    )


# ── 429 Rate Limit ────────────────────────────────────────────────────────────
class RateLimitException(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests — please try again later"


# ── 503 Service Unavailable ───────────────────────────────────────────────────
class ServiceUnavailableException(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"


# ── Gmail-Specific ─────────────────────────────────────────────────────────────
class GmailNotConnectedException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "GMAIL_NOT_CONNECTED"
    message = "Gmail account is not connected"


class GmailTokenRevokedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "GMAIL_TOKEN_REVOKED"
    message = "Gmail access has been revoked — please reconnect your account"


class SyncAlreadyRunningException(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "SYNC_ALREADY_RUNNING"
    message = "A sync job is already running for your account"


# ── Response Helper ────────────────────────────────────────────────────────────
def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            },
        },
    )


def _add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    from app.config import settings as _settings
    origin = request.headers.get("origin", "")
    if origin and ("*" in _settings.allowed_origins or origin in _settings.allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


# ── Exception Handlers ─────────────────────────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI application."""
    from slowapi.errors import RateLimitExceeded

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "app_exception",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return _error_response(
            exc.status_code, exc.error_code, exc.message, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Flatten Pydantic v2 error list into a readable dict
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            field_errors.setdefault(field, []).append(error["msg"])

        logger.info(
            "validation_error",
            path=request.url.path,
            errors=field_errors,
        )
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed",
            {"fields": field_errors},
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
    ) -> JSONResponse:
        logger.warning(
            "rate_limit_exceeded",
            path=request.url.path,
        )
        response = _error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "RATE_LIMIT_EXCEEDED",
            "Too many requests — please try again later",
        )
        return _add_cors_headers(request, response)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            exc_type=type(exc).__name__,
        )
        import traceback
        response = _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            f"An unexpected error occurred: {str(exc)}",
            details={
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc()
            }
        )
        # IMPORTANT: @app.exception_handler(Exception) is used by Starlette's
        # ServerErrorMiddleware, which is the OUTERMOST layer — above CORSMiddleware.
        # This means the response bypasses CORSMiddleware and never gets CORS headers.
        # Without these headers, the browser blocks the response with a CORS policy error,
        # hiding the real 500 error from the frontend. Add headers manually here.
        return _add_cors_headers(request, response)
