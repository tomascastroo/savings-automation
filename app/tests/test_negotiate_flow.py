import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.tests.factories import create_user, create_provider, create_service, create_bill
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_negotiate_success(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    user = await create_user(db, email="negotiate@test.com")
    provider = await create_provider(db, "Negotiate Provider")
    service = await create_service(db, user.id, provider.id)
    await create_bill(db, service.id, 100.0)

    response = await async_client.post(f"/services/{service.id}/negotiate", headers=user_auth_header)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "proposed"
    assert data["initial_amount"] == 100.0

@pytest.mark.asyncio
async def test_negotiate_rate_limit(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    user = await create_user(db, email="ratelimit@test.com")
    provider = await create_provider(db, "Rate Limit Provider")
    service = await create_service(db, user.id, provider.id)
    await create_bill(db, service.id, 100.0)

    # First call should succeed
    response1 = await async_client.post(f"/services/{service.id}/negotiate", headers=user_auth_header)
    assert response1.status_code == 201

    # Second call should be rate limited
    response2 = await async_client.post(f"/services/{service.id}/negotiate", headers=user_auth_header)
    assert response2.status_code == 429

@pytest.mark.asyncio
async def test_confirm_negotiation_success(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    user = await create_user(db, email="confirm@test.com")
    provider = await create_provider(db, "Confirm Provider")
    service = await create_service(db, user.id, provider.id)
    await create_bill(db, service.id, 100.0)

    neg_response = await async_client.post(f"/services/{service.id}/negotiate", headers=user_auth_header)
    neg_id = neg_response.json()["id"]

    valid_until = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    payload = {
        "accepted": True,
        "new_amount": 80.0,
        "valid_until": valid_until
    }
    response = await async_client.post(f"/negotiations/{neg_id}/confirm", json=payload, headers=user_auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["new_amount"] == 80.0
    assert data["discount_abs"] == 20.0
    assert data["discount_pct"] == 0.2

@pytest.mark.asyncio
async def test_confirm_negotiation_invalid_data(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    user = await create_user(db, email="invalid@test.com")
    provider = await create_provider(db, "Invalid Provider")
    service = await create_service(db, user.id, provider.id)
    await create_bill(db, service.id, 100.0)

    neg_response = await async_client.post(f"/services/{service.id}/negotiate", headers=user_auth_header)
    neg_id = neg_response.json()["id"]

    payload = {
        "accepted": True,
        "new_amount": 120.0, # Higher than initial amount
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    }
    response = await async_client.post(f"/negotiations/{neg_id}/confirm", json=payload, headers=user_auth_header)
    assert response.status_code == 422
