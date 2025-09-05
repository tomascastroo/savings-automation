import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_endpoint_requires_admin_role(async_client: AsyncClient, user_auth_header: dict):
    # Using the providers endpoint as an example of an admin endpoint
    response = await async_client.get("/admin/providers/", headers=user_auth_header)
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_endpoint_requires_auth(async_client: AsyncClient):
    # Using the dashboard endpoint as an example of an authenticated endpoint
    response = await async_client.get("/dashboard/me")
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_invalid_jwt_fails(async_client: AsyncClient):
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await async_client.get("/dashboard/me", headers=headers)
    assert response.status_code in [401, 403]
