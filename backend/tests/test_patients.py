import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def _second_clinic_headers(client: httpx.AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/auth/signup",
        json={"clinic_name": "Other", "name": "Dr B", "phone": "8888888888", "password": "secret123"},
    )
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def test_create_and_list(client: httpx.AsyncClient, auth_headers):
    r = await client.post(
        "/api/patients",
        headers=auth_headers,
        json={"name": "Asha Kumar", "phone": "9876543210", "gender": "female"},
    )
    assert r.status_code == 200
    patient = r.json()
    assert patient["id"] > 0

    listed = await client.get("/api/patients", headers=auth_headers)
    assert [p["name"] for p in listed.json()] == ["Asha Kumar"]


async def test_search_by_name_prefix(client: httpx.AsyncClient, auth_headers):
    await client.post("/api/patients", headers=auth_headers, json={"name": "Ravi Verma"})
    await client.post("/api/patients", headers=auth_headers, json={"name": "Sunita Devi"})
    listed = await client.get("/api/patients?q=ravi", headers=auth_headers)
    assert len(listed.json()) == 1
    assert listed.json()[0]["name"] == "Ravi Verma"


async def test_cross_clinic_patient_is_404(client: httpx.AsyncClient, auth_headers):
    created = await client.post(
        "/api/patients", headers=auth_headers, json={"name": "Private Patient"}
    )
    pid = created.json()["id"]
    other = await _second_clinic_headers(client)
    resp = await client.get(f"/api/patients/{pid}", headers=other)
    assert resp.status_code == 404
