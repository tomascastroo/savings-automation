import os
import asyncio
import json
import shutil
import tempfile
import contextlib
from typing import AsyncGenerator

import pytest
import anyio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base
from app.dependencies import get_db

TEST_STORAGE = tempfile.mkdtemp(prefix="sa-tests-")
os.environ.setdefault("STORAGE_DIR", TEST_STORAGE)
os.environ.setdefault("JWT_SECRET", "test-secret")

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DB_URL, echo=False, poolclass=NullPool, future=True,
)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def _create_test_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@contextlib.asynccontextmanager
async def _override_db():
    async with SessionLocal() as session:
        yield session

@pytest.fixture(autouse=True, scope="session")
async def _override_dependencies(_create_test_schema):
    app.dependency_overrides[get_db] = lambda: _override_db()
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="session", autouse=True)
def _cleanup_storage():
    try:
        yield
    finally:
        shutil.rmtree(TEST_STORAGE, ignore_errors=True)

def _make_jwt(user_id: int, is_admin: bool = False) -> str:
    import time, jwt
    payload = {"sub": str(user_id), "is_admin": is_admin, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")

@pytest.fixture
def admin_auth_header() -> dict[str, str]:
    # Assuming user with ID 1 is an admin for test purposes
    return {"Authorization": f"Bearer {_make_jwt(user_id=1, is_admin=True)}"}

@pytest.fixture
def user_auth_header() -> dict[str, str]:
    # Assuming user with ID 2 is a regular user
    return {"Authorization": f"Bearer {_make_jwt(user_id=2, is_admin=False)}"}

@pytest.fixture
def fake_pdf_bytes() -> bytes:
    # A minimal valid PDF file content
    return b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000058 00000 n\n0000000106 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"

@pytest.fixture(autouse=True)
def mock_ocr(monkeypatch):
    for target in (
        "app.services.ocr.extract_text",
        "app.services.pdf.extract_text",
        "app.lib.ocr.extract_text",
    ):
        try:
            import importlib
            module_path, func_name = target.rsplit(".", 1)
            module = importlib.import_module(module_path)
            if hasattr(module, func_name):
                def _fake_extract_text(file_path: str):
                    return {
                        "text": "FAKE OCR TEXT\nprovider: Test Provider\namount: 10000",
                        "pages": 1,
                        "parsed": {"provider_hint": "Test Provider"},
                    }
                monkeypatch.setattr(module, func_name, _fake_extract_text)
                break
        except ModuleNotFoundError:
            continue
    yield

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
