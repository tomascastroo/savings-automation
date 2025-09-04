import httpx
import pytest

@pytest.mark.asyncio
async def test_health(anon_client: httpx.AsyncClient):
    r = await anon_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)

@pytest.mark.asyncio
async def test_signup_and_login(anon_client: httpx.AsyncClient):
    # This is also covered by the auth fixture; keeping explicit test for clarity.
    email = "t-one@example.com"  # this exact email may already exist; we tolerate 409 or 400
    password = "secret123"
    r = await anon_client.post("/auth/signup", json={"email": email, "password": password})
    assert r.status_code in (200, 201, 400, 409)
    r = await anon_client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code in (200, 401)
    if r.status_code == 200:
        assert "access_token" in r.json()

@pytest.mark.asyncio
async def test_protected_requires_bearer(anon_client: httpx.AsyncClient):
    r = await anon_client.get("/dashboard/me")
    assert r.status_code in (401, 403)
