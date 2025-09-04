import asyncio
import httpx
import pytest
import pytest_asyncio
import fakeredis.aioredis
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base
from app.dependencies import get_db

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency override for getting a test database session.
    """
    async with TestingSessionLocal() as session:
        yield session

# Apply the override for the test environment
app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
def mock_redis(monkeypatch):
    """
    Mocks the redis client for all tests to avoid real network calls.
    We patch the function in all namespaces where it's imported.
    """
    fake_redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.utils.redis_client.get_redis", lambda: fake_redis_client)
    monkeypatch.setattr("app.services.rate_limit.get_redis", lambda: fake_redis_client)
    monkeypatch.setattr("app.services.payment.get_redis", lambda: fake_redis_client)


@pytest_asyncio.fixture(autouse=True)
def override_storage_dir(monkeypatch, tmp_path):
    """
    For the duration of a test, point the storage directory to a temporary path
    to avoid permission errors and keep the test environment clean.
    """
    from app.config import settings
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

@pytest_asyncio.fixture(scope="function", autouse=True)
async def auto_setup_database():
    """
    Automatically creates and drops database tables for each test function,
    ensuring a clean state and test isolation.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session to tests that need to interact with the DB
    directly (e.g., for setting up state with helper functions).
    """
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def anon_client() -> httpx.AsyncClient:
    """
    An anonymous (non-authenticated) test client that talks to the in-memory app.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def auth_client(anon_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """
    An authenticated test client.
    Creates a user (ID=1, so admin) and returns a client with their token.
    """
    # Signup
    email = "admin@example.com"
    password = "secret123"
    signup_response = await anon_client.post("/auth/signup", json={"email": email, "password": password})
    assert signup_response.status_code == 200

    # Login
    login_response = await anon_client.post("/auth/login", json={"email": email, "password": password})
    login_response.raise_for_status()
    token = login_response.json()["access_token"]

    # Return authenticated client
    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
        yield c