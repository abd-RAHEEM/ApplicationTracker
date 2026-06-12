import os
import pytest
import pytest_asyncio

# Set dummy environment variables for Pydantic Settings validation in tests
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_secret_key_at_least_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "dummy_encryption_key_at_least_32_bytes_long_in_base64_format=")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base

# Use SQLite in-memory for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingSessionLocal() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def session(db_session):
    """Alias for db_session to match test parameter expectations."""
    yield db_session

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create a test client that overrides the get_async_session dependency."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db.session import get_async_session

    async def override_get_async_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_async_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    """Create a test user in the database."""
    from app.core.security import hash_password
    from app.models.user import User
    user = User(
        full_name="Test User",
        username="testuser",
        hashed_password=hash_password("Password123!"),
        is_active=True,
        is_email_verified=False,
        is_onboarding_completed=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user

@pytest_asyncio.fixture(scope="function")
async def verified_user(db_session):
    """Create a verified test user with email verified and onboarding completed."""
    from app.core.security import hash_password
    from app.models.user import User
    user = User(
        full_name="Verified User",
        username="verifieduser",
        hashed_password=hash_password("Password123!"),
        is_active=True,
        is_email_verified=True,
        is_onboarding_completed=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()
    return user

@pytest.fixture(autouse=True)
def mock_celery_delay(monkeypatch):
    """Automatically mock Celery tasks delay method during tests."""
    from unittest.mock import MagicMock
    from app.worker.tasks import run_incremental_sync
    mock_delay = MagicMock()
    monkeypatch.setattr(run_incremental_sync, "delay", mock_delay)
    return mock_delay

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the SlowAPI rate limiter storage between tests."""
    from app.core.rate_limiter import limiter
    try:
        limiter._limiter.storage.reset()
    except Exception:
        pass
