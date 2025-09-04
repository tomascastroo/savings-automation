import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ocr import OcrResult

@pytest.mark.asyncio
async def test_full_mvp_flow(auth_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch):
    """
    Tests the entire MVP flow from bill upload to fee collection.
    """
    # --- 1. Setup: Admin creates a Provider and a cheaper ProviderPlan ---
    provider_resp = await auth_client.post("/admin/providers/", json={"name": "Movistar", "country": "AR"})
    assert provider_resp.status_code == 201
    provider_id = provider_resp.json()["id"]

    plan_resp = await auth_client.post("/admin/plans/", json={
        "provider_id": provider_id,
        "name": "Fiber 300MB Cheaper",
        "category": "internet",
        "price": 5000.0,
        "currency": "ARS"
    })
    assert plan_resp.status_code == 201

    # --- 2. User uploads a bill that is more expensive than the available plan ---
    # The user (id=1 from auth_client) needs a Service to upload a bill against
    from app.tests._helpers import ensure_provider_and_service
    _, service_id = await ensure_provider_and_service(db=db_session, user_id=1, provider_kwargs={"name": "Movistar"})

    # Mock OCR to return a high bill amount
    async def mock_extract_text(*args, **kwargs):
        return OcrResult(text="Total a pagar: $10000.00", pages=1)
    monkeypatch.setattr("app.services.ocr.TesseractOcrEngine.extract_text", mock_extract_text)

    from app.tests._helpers import make_dummy_image_bytes
    img = make_dummy_image_bytes()
    files = {"file": ("bill.png", img, "image/png")}

    upload_resp = await auth_client.post("/bills", params={"service_id": service_id}, files=files)
    assert upload_resp.status_code == 200 # BillRead schema returns 200

    # --- 3. System finds an opportunity and user starts negotiation ---
    neg_resp = await auth_client.post(f"/services/{service_id}/negotiate")
    assert neg_resp.status_code == 201
    neg_data = neg_resp.json()
    assert neg_data["strategy"] == "switch"
    negotiation_id = neg_data["id"]

    # --- 4. User confirms the successful negotiation ---
    confirm_resp = await auth_client.post(f"/negotiations/{negotiation_id}/confirm", json={"new_amount": 5000.0})
    assert confirm_resp.status_code == 201
    confirm_data = confirm_resp.json()
    assert confirm_data["payment_status"] == "paid"
    assert confirm_data["fee_amount"] > 0

    # --- 5. (Bonus) Admin checks KPIs ---
    kpi_resp = await auth_client.get("/admin/kpis")
    assert kpi_resp.status_code == 200
    kpi_data = kpi_resp.json()
    assert kpi_data["total_saving_achieved"] > 0
    assert kpi_data["total_fees_collected"] > 0
    assert kpi_data["successful_negotiations"] == 1


@pytest.mark.asyncio
async def test_provider_plan_crud(auth_client: httpx.AsyncClient):
    """
    Tests the CRUD functionality for ProviderPlans.
    """
    # First, create a provider to associate plans with
    provider_resp = await auth_client.post("/admin/providers/", json={"name": "TestProviderForPlans", "country": "CL"})
    assert provider_resp.status_code == 201
    provider_id = provider_resp.json()["id"]

    # 1. Create a plan
    plan_data = {
        "provider_id": provider_id,
        "name": "Plan Basico",
        "category": "mobile",
        "price": 30.0,
    }
    create_resp = await auth_client.post("/admin/plans/", json=plan_data)
    assert create_resp.status_code == 201
    created_plan = create_resp.json()
    assert created_plan["name"] == plan_data["name"]

    # 2. Read the plan
    plan_id = created_plan["id"]
    get_resp = await auth_client.get(f"/admin/plans/?limit=10") # Assuming the endpoint is /admin/plans/
    assert get_resp.status_code == 200
    assert any(p["id"] == plan_id for p in get_resp.json())


@pytest.mark.asyncio
async def test_refund_flow(auth_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch):
    """
    Tests that a paid fee can be successfully refunded by an admin.
    """
    # This test re-creates the full flow to get a Fee in a "paid" state.

    # 1. Setup
    provider_resp = await auth_client.post("/admin/providers/", json={"name": "RefundTelco", "country": "AR"})
    provider_id = provider_resp.json()["id"]
    plan_resp = await auth_client.post("/admin/plans/", json={"provider_id": provider_id, "name": "Plan Refundable", "category": "internet", "price": 1000.0})

    from app.tests._helpers import ensure_provider_and_service
    _, service_id = await ensure_provider_and_service(db=db_session, user_id=1, provider_kwargs={"name": "RefundTelco"})

    async def mock_extract_text(*args, **kwargs): return OcrResult(text="Total: $2000", pages=1)
    monkeypatch.setattr("app.services.ocr.TesseractOcrEngine.extract_text", mock_extract_text)

    from app.tests._helpers import make_dummy_image_bytes
    files = {"file": ("bill.png", make_dummy_image_bytes(), "image/png")}
    await auth_client.post("/bills", params={"service_id": service_id}, files=files)

    neg_resp = await auth_client.post(f"/services/{service_id}/negotiate")
    negotiation_id = neg_resp.json()["id"]

    confirm_resp = await auth_client.post(f"/negotiations/{negotiation_id}/confirm", json={"new_amount": 1000.0})
    fee_id = confirm_resp.json()["fee_id"]

    # 2. Request Refund
    refund_resp = await auth_client.post("/admin/refunds/", json={"fee_id": fee_id, "reason": "Customer complaint"})
    assert refund_resp.status_code == 200
    refund_data = refund_resp.json()
    assert refund_data["status"] == "refunded"
    assert refund_data["fee_id"] == fee_id

    # 3. Verify fee status changed
    from app.models.payment import Fee, PaymentStatus
    fee = await db_session.get(Fee, fee_id)
    assert fee.payment_status == PaymentStatus.refunded
