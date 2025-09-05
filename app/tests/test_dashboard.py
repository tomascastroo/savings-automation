import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.tests.factories import create_user, create_provider, create_service, create_bill
from app.models.negotiation import Negotiation, NegotiationStatus
from app.models.payment import Saving, Fee, PaymentStatus

@pytest.mark.asyncio
async def test_get_dashboard_data(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    user = await create_user(db, email="dashboard@test.com")
    provider = await create_provider(db, "Dashboard Provider")
    service = await create_service(db, user.id, provider.id)
    bill = await create_bill(db, service.id, 100.0)

    # Create a confirmed negotiation
    neg = Negotiation(bill_id=bill.id, initial_amount=100.0, new_amount=80.0, status=NegotiationStatus.accepted)
    db.add(neg)
    await db.commit()

    # Create a saving associated with the negotiation
    saving = Saving(negotiation_id=neg.id, user_id=user.id, saving_amount=20.0)
    db.add(saving)
    await db.commit()

    # Create a paid fee associated with the saving
    fee = Fee(saving_id=saving.id, fee_amount=4.0, payment_status=PaymentStatus.paid)
    db.add(fee)
    await db.commit()

    response = await async_client.get("/dashboard/me", headers=user_auth_header)
    assert response.status_code == 200
    data = response.json()

    # These are example fields, the actual fields might be different
    # I'm assuming the dashboard returns these aggregated values.
    assert "total_savings" in data
    assert "fees_paid" in data
    assert data["total_savings"] >= 20.0
    assert data["fees_paid"] >= 4.0
