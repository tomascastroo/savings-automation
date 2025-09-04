import pytest
import httpx

@pytest.mark.asyncio
async def test_provider_crud_flow(auth_client: httpx.AsyncClient):
    """
    Tests the full CRUD lifecycle for providers via the admin endpoint.
    """
    # 1. Create a new provider
    provider_data = {
        "name": "TestTelco",
        "country": "AR",
        "website": "https://testtelco.com"
    }
    r = await auth_client.post("/admin/providers/", json=provider_data)
    assert r.status_code == 201, f"Failed to create provider: {r.text}"
    created_provider = r.json()
    provider_id = created_provider["id"]

    assert created_provider["name"] == provider_data["name"]
    assert created_provider["country"] == provider_data["country"]

    # 2. Read the provider
    r = await auth_client.get(f"/admin/providers/{provider_id}")
    assert r.status_code == 200
    read_provider = r.json()
    assert read_provider["name"] == provider_data["name"]

    # 3. List providers to ensure it's in the list
    r = await auth_client.get("/admin/providers/")
    assert r.status_code == 200
    provider_list = r.json()
    assert isinstance(provider_list, list)
    assert any(p["id"] == provider_id for p in provider_list)

    # 4. Update the provider
    update_data = {"website": "https://new.testtelco.com"}
    r = await auth_client.patch(f"/admin/providers/{provider_id}", json=update_data)
    assert r.status_code == 200, f"Failed to update provider: {r.text}"
    updated_provider = r.json()
    assert updated_provider["website"] == update_data["website"]
    assert updated_provider["name"] == provider_data["name"] # Ensure name is unchanged

    # 5. Delete the provider
    r = await auth_client.delete(f"/admin/providers/{provider_id}")
    assert r.status_code == 204

    # 6. Verify it's deleted
    r = await auth_client.get(f"/admin/providers/{provider_id}")
    assert r.status_code == 404
