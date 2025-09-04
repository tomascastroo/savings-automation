import pytest
import httpx
from ._helpers import ensure_provider_and_service, make_dummy_image_bytes

@pytest.mark.asyncio
async def test_invalid_token_rejected(anon_client: httpx.AsyncClient):
    r = await anon_client.get("/dashboard/me", headers={"Authorization": "Bearer invalid.token"})
    assert r.status_code in (401, 403)

@pytest.mark.asyncio
async def test_rate_limit_provider_account(auth_client: httpx.AsyncClient, auth: dict):
    user_id = int(auth["user"]["id"])
    # Create a single provider account and attempt to negotiate twice
    _, sid = await ensure_provider_and_service(user_id=user_id)
    img = make_dummy_image_bytes()
    files = {"file": ("bill.png", img, "image/png")}
    r = await auth_client.post("/bills", params={"service_id": sid}, files=files)
    assert r.status_code in (200, 201)
    # First negotiation should succeed
    r1 = await auth_client.post(f"/services/{sid}/negotiate", json={"strategy": "retention"})
    assert r1.status_code in (200, 201)
    # Second negotiation should be rate-limited or otherwise refused
    r2 = await auth_client.post(f"/services/{sid}/negotiate", json={"strategy": "retention"})
    assert r2.status_code in (429, 400, 409), f"Expected rate-limit-ish response, got {r2.status_code} {r2.text}"
