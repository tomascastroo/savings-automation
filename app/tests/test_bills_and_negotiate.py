import io
import pytest

async def _create_provider(async_client, admin_auth_header):
    payload = {"name": "Test Provider", "country": "US", "website": "https://example.com"}
    r = await async_client.post("/admin/providers/", headers=admin_auth_header, json=payload)
    if r.status_code in (200, 201):
        return r.json()["id"]
    r = await async_client.get("/admin/providers/", headers=admin_auth_header)
    return r.json()[0]["id"]

async def _create_service(async_client, admin_auth_header, provider_id: int):
    for path in ("/admin/services/", "/services"):
        resp = await async_client.post(
            path,
            headers=admin_auth_header,
            json={
                "user_id": 1,
                "provider_id": provider_id,
                "category": "internet",
                "provider_acct": "ACC-001",
                "alias": "Casa",
                "active": True,
            },
        )
        if resp.status_code in (200, 201):
            return resp.json()["id"]
        if resp.status_code not in (404, 405):
            break
    pytest.skip("No service creation endpoint found")

async def test_bills_upload_and_negotiate_flow(async_client, admin_auth_header):
    provider_id = await _create_provider(async_client, admin_auth_header)
    service_id = await _create_service(async_client, admin_auth_header, provider_id)

    fake_pdf = b"%PDF-1.4\n%FAKE\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"
    files = {"file": ("bill.pdf", io.BytesIO(fake_pdf), "application/pdf")}

    r = await async_client.post(f"/bills?service_id={service_id}", headers=admin_auth_header, files=files)
    assert r.status_code in (200, 201), r.text
    bill = r.json()
    bill_id = bill["id"]

    r = await async_client.get(f"/bills/{bill_id}", headers=admin_auth_header)
    assert r.status_code == 200

    payload = {"bill_id": bill_id}
    r = await async_client.post(f"/services/{service_id}/negotiate", headers=admin_auth_header, json=payload)
    assert r.status_code in (200, 201), r.text
    neg_id = r.json()["id"]

    confirm = {
        "accept": True,
        "new_amount": 8000.00,
        "valid_until": "2025-12-31T23:59:59Z"
    }
    r = await async_client.post(f"/negotiations/{neg_id}/confirm", headers=admin_auth_header, json=confirm)
    assert r.status_code in (200, 201), r.text
