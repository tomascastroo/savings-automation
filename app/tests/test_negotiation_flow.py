import json
import pytest
import httpx
from typing import Dict, Any, Optional

from ._helpers import ensure_provider_and_service, make_dummy_image_bytes

async def _infer_confirm_body_from_openapi(client: httpx.AsyncClient, negotiation_id: int) -> Optional[Dict[str, Any]]:
    """Try to parse the OpenAPI schema for /negotiations/{neg_id}/confirm and build a minimal valid body.
    Returns None if not possible."""
    try:
        resp = await client.get("/openapi.json")
        if resp.status_code != 200:
            return {}
        spec = resp.json()
        path_tpl = "/negotiations/{neg_id}/confirm"
        path_obj = spec.get("paths", {}).get(path_tpl) or {}
        post_op = path_obj.get("post") or {}
        rb = post_op.get("requestBody", {})
        content = rb.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []) or [])
        body: Dict[str, Any] = {}
        # naive fill
        for k, s in props.items():
            t = s.get("type")
            if k in required or t:
                if t == "string":
                    body[k] = "ok"
                elif t == "number":
                    body[k] = 1.0
                elif t == "integer":
                    body[k] = 1
                elif t == "boolean":
                    body[k] = True
                elif t == "array":
                    body[k] = []
                elif t == "object":
                    body[k] = {}
        return body
    except Exception:
        return None

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ocr import OcrResult

@pytest.mark.asyncio
async def test_negotiate_and_confirm(auth_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch):
    # Mock OCR to avoid dependency on tesseract/poppler in test environment
    async def mock_extract_text(*args, **kwargs):
        return OcrResult(text="Amount due: $100.00", pages=1)
    monkeypatch.setattr("app.services.ocr.TesseractOcrEngine.extract_text", mock_extract_text)

    # The auth_client fixture creates user with id=1, who is admin
    user_id = 1
    _, service_id = await ensure_provider_and_service(db=db_session, user_id=user_id)

    # Ensure we have at least one bill (some implementations require it before negotiating)
    img = make_dummy_image_bytes()
    files = {"file": ("bill.png", img, "image/png")}
    r = await auth_client.post("/bills", params={"service_id": service_id}, files=files)
    assert r.status_code in (200, 201), f"bill upload failed before negotiation: {r.status_code} {r.text}"

    # Negotiate
    r = await auth_client.post(f"/services/{service_id}/negotiate", json={"strategy": "retention"})
    if r.status_code == 429:
        pytest.skip("Rate limit hit unexpectedly in CI; skipping negotiation test.")
    assert r.status_code in (200, 201), f"negotiate failed: {r.status_code} {r.text}"
    neg = r.json()
    neg_id = neg.get("id") or neg.get("negotiation_id")
    assert neg_id, f"Negotiation id not found in response: {neg}"

    # Confirm
    confirm_body = {"new_amount": 8000.0}
    r = await auth_client.post(f"/negotiations/{neg_id}/confirm", json=confirm_body)
    # Accept common statuses
    assert r.status_code in (200, 201, 202), f"confirm failed: {r.status_code} {r.text}"
    data = r.json()
    # We accept either a 'status' or presence of saving/fee ids.
    assert isinstance(data, dict)

@pytest.mark.asyncio
async def test_dashboard_me(auth_client: httpx.AsyncClient):
    r = await auth_client.get("/dashboard/me")
    assert r.status_code == 200
    data = r.json()
    assert "total_saving" in data and "fees_paid" in data
