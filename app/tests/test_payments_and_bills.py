import httpx
import pytest

from ._helpers import ensure_provider_and_service, make_dummy_image_bytes

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ocr import OcrResult

@pytest.mark.asyncio
async def test_setup_payment_and_upload_bill(auth_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch):
    # Mock OCR to avoid dependency on tesseract/poppler in test environment
    async def mock_extract_text(*args, **kwargs):
        return OcrResult(text="Amount due: $123.45", pages=1)
    monkeypatch.setattr("app.services.ocr.TesseractOcrEngine.extract_text", mock_extract_text)

    # 1) setup payment method
    r = await auth_client.post("/auth/payments/setup", json={"provider": "stripe", "pm_token": "tok_test_123"})
    assert r.status_code in (200, 201), f"setup payment failed: {r.status_code} {r.text}"
    data = r.json()
    assert "payment_method_id" in data and "authorization_id" in data

    # 2) seed provider + service directly in DB
    # The auth_client fixture creates user with id=1
    user_id = 1
    _, service_id = await ensure_provider_and_service(db=db_session, user_id=user_id)

    # 3) upload a bill (dummy image)
    image_bytes = make_dummy_image_bytes()
    files = {"file": ("bill.png", image_bytes, "image/png")}
    r = await auth_client.post(f"/bills", params={"service_id": service_id}, files=files)
    assert r.status_code in (200, 201), f"bill upload failed: {r.status_code} {r.text}"
    bill = r.json()
    assert "id" in bill and bill.get("amount_due") is not None
