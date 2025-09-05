import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.tests.factories import create_provider

@pytest.mark.asyncio
async def test_create_provider_success(async_client: AsyncClient, admin_auth_header: dict):
    response = await async_client.post("/admin/providers/", json={"name": "Test Provider", "country": "AR"}, headers=admin_auth_header)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Provider"

@pytest.mark.asyncio
async def test_create_provider_unauthorized(async_client: AsyncClient, user_auth_header: dict):
    response = await async_client.post("/admin/providers/", json={"name": "Test Provider"}, headers=user_auth_header)
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_get_providers_success(async_client: AsyncClient, db: AsyncSession, admin_auth_header: dict):
    await create_provider(db, "Provider 1")
    await create_provider(db, "Provider 2")
    response = await async_client.get("/admin/providers/", headers=admin_auth_header)
    assert response.status_code == 200
    assert len(response.json()) >= 2

@pytest.mark.asyncio
async def test_get_provider_success(async_client: AsyncClient, db: AsyncSession, admin_auth_header: dict):
    provider = await create_provider(db, "Detail Provider")
    response = await async_client.get(f"/admin/providers/{provider.id}", headers=admin_auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Detail Provider"

@pytest.mark.asyncio
async def test_update_provider_success(async_client: AsyncClient, db: AsyncSession, admin_auth_header: dict):
    provider = await create_provider(db, "Update Provider")
    response = await async_client.put(f"/admin/providers/{provider.id}", json={"name": "Updated Provider"}, headers=admin_auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Provider"

@pytest.mark.asyncio
async def test_delete_provider_success(async_client: AsyncClient, db: AsyncSession, admin_auth_header: dict):
    provider = await create_provider(db, "Delete Provider")
    response = await async_client.delete(f"/admin/providers/{provider.id}", headers=admin_auth_header)
    assert response.status_code == 204

    # Verify it's gone
    response = await async_client.get(f"/admin/providers/{provider.id}", headers=admin_auth_header)
    assert response.status_code == 404
