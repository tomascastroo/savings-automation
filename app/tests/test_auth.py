import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.tests.factories import create_user

@pytest.mark.asyncio
async def test_signup_success(async_client: AsyncClient, db: AsyncSession):
    response = await async_client.post("/auth/signup", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_signup_duplicate_email(async_client: AsyncClient, db: AsyncSession):
    await create_user(db, "test@example.com")
    response = await async_client.post("/auth/signup", json={"email": "test@example.com", "password": "password"})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db: AsyncSession):
    await create_user(db, "test@example.com", "password")
    response = await async_client.post("/auth/login", data={"username": "test@example.com", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, db: AsyncSession):
    await create_user(db, "test@example.com", "password")
    response = await async_client.post("/auth/login", data={"username": "test@example.com", "password": "wrongpassword"})
    assert response.status_code == 401
