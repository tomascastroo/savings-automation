import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.tests.factories import create_user, create_provider, create_service, create_bill
from io import BytesIO

@pytest.mark.asyncio
async def test_upload_bill_success(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict, fake_pdf_bytes: bytes):
    user = await create_user(db, email="testuser@bill.com")
    provider = await create_provider(db, "Bill Provider")
    service = await create_service(db, user.id, provider.id)

    files = {"file": ("bill.pdf", BytesIO(fake_pdf_bytes), "application/pdf")}
    response = await async_client.post(f"/bills?service_id={service.id}", files=files, headers=user_auth_header)

    assert response.status_code == 201
    data = response.json()
    assert data["service_id"] == service.id
    assert "id" in data

@pytest.mark.asyncio
async def test_upload_bill_missing_service_id(async_client: AsyncClient, user_auth_header: dict, fake_pdf_bytes: bytes):
    files = {"file": ("bill.pdf", BytesIO(fake_pdf_bytes), "application/pdf")}
    response = await async_client.post("/bills", files=files, headers=user_auth_header)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_upload_bill_service_not_owned(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict, fake_pdf_bytes: bytes):
    owner = await create_user(db, email="owner@bill.com")
    provider = await create_provider(db, "Owned Provider")
    service = await create_service(db, owner.id, provider.id)

    # Authenticated user is different from the service owner
    await create_user(db, email="other@bill.com")

    files = {"file": ("bill.pdf", BytesIO(fake_pdf_bytes), "application/pdf")}
    response = await async_client.post(f"/bills?service_id={service.id}", files=files, headers=user_auth_header)
    assert response.status_code in [403, 404]

@pytest.mark.asyncio
async def test_get_bill_success(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    user = await create_user(db, email="testuser@getbill.com")
    provider = await create_provider(db, "Get Bill Provider")
    service = await create_service(db, user.id, provider.id)
    bill = await create_bill(db, service.id, 200.0)

    response = await async_client.get(f"/bills/{bill.id}", headers=user_auth_header)
    assert response.status_code == 200
    assert response.json()["id"] == bill.id

@pytest.mark.asyncio
async def test_get_bill_not_owned(async_client: AsyncClient, db: AsyncSession, user_auth_header: dict):
    owner = await create_user(db, email="owner@getbill.com")
    provider = await create_provider(db, "Get Bill Owned Provider")
    service = await create_service(db, owner.id, provider.id)
    bill = await create_bill(db, service.id, 250.0)

    # Authenticated user is different from the bill owner
    await create_user(db, email="other@getbill.com")

    response = await async_client.get(f"/bills/{bill.id}", headers=user_auth_header)
    assert response.status_code in [403, 404]
