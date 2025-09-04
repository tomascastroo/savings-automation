import pytest
import httpx
from ._helpers import ensure_provider_and_service, make_dummy_image_bytes

@pytest.mark.asyncio
async def test_invalid_token_rejected(anon_client: httpx.AsyncClient):
    r = await anon_client.get("/dashboard/me", headers={"Authorization": "Bearer invalid.token"})
    assert r.status_code in (401, 403)

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ocr import OcrResult

@pytest.mark.asyncio
async def test_rate_limit_provider_account(auth_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch):
    # Mock OCR to avoid dependency on tesseract/poppler in test environment
    async def mock_extract_text(*args, **kwargs):
        return OcrResult(text="Amount due: $99.99", pages=1)
    monkeypatch.setattr("app.services.ocr.TesseractOcrEngine.extract_text", mock_extract_text)

    # The auth_client fixture creates user with id=1
    user_id = 1
    # Create a single provider account and attempt to negotiate twice
    _, sid = await ensure_provider_and_service(db=db_session, user_id=user_id)
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
