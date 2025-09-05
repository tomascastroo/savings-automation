import pytest

async def test_health(async_client):
    r = await async_client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

async def test_admin_providers_crud(async_client, admin_auth_header):
    r = await async_client.get("/admin/providers/", headers=admin_auth_header)
    assert r.status_code == 200
    assert r.json() == []

    payload = {"name": "Test Provider", "country": "US", "website": "https://example.com"}
    r = await async_client.post("/admin/providers/", headers=admin_auth_header, json=payload)
    assert r.status_code in (200, 201)
    created = r.json()
    assert created["name"] == "Test Provider"
    pid = created["id"]

    r = await async_client.post("/admin/providers/", headers=admin_auth_header, json=payload)
    assert r.status_code in (400, 409)
    assert "exists" in r.text.lower()

    r = await async_client.get("/admin/providers/", headers=admin_auth_header)
    items = r.json()
    assert any(i["id"] == pid for i in items)
