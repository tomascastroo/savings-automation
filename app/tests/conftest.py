# app/tests/conftest.py

import os
import asyncio
import httpx
import pytest
import pytest_asyncio  # ← IMPORTANTE

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Si tenías un event_loop redefinido, mantenelo así:
@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Crea un loop por sesión de tests (evita warnings)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def anon_client():
    """Cliente HTTP sin autenticación apuntando a la API en BASE_URL."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0, follow_redirects=True) as c:
        yield c

@pytest_asyncio.fixture
async def auth(anon_client):
    """Crea usuario de prueba y devuelve dict con token y user."""
    # signup (tolera 409 si ya existe)
    email = "t-one@example.com"
    password = "secret123"
    r = await anon_client.post("/auth/signup", json={"email": email, "password": password})
    if r.status_code not in (200, 201, 400, 409):
        r.raise_for_status()

    # login
    r = await anon_client.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    data = r.json()
    return {
        "token": data["access_token"],
        "user": {"email": email, "id": data.get("user", {}).get("id", 1)},  # fallback simple
    }

@pytest_asyncio.fixture
async def auth_client(auth):
    """Cliente HTTP autenticado con Bearer token."""
    headers = {"Authorization": f"Bearer {auth['token']}"}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0, headers=headers, follow_redirects=True) as c:
        yield c

# (Opcional) Si tus tests de rate-limit comparten estado, reseteá Redis entre tests:
# from app.utils.redis_client import get_redis
# @pytest_asyncio.fixture(autouse=True)
# async def _flush_rate_limit_keys():
#     r = await get_redis()
#     # Limpiamos solo llaves del rate-limit para no romper otras cosas
#     for k in await r.keys("prov:*"):
#         await r.delete(k)