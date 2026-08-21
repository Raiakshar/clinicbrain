import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_search_finds_note_text(client: AsyncClient, auth_headers):
    pid = (
        await client.post("/api/patients", headers=auth_headers, json={"name": "Search P"})
    ).json()["id"]
    token = "xylophoneunique"
    await client.post(
        f"/api/patients/{pid}/events",
        headers=auth_headers,
        json={"type": "note", "payload": {"text": f"patient mentioned {token} in history"}},
    )
    resp = await client.get(f"/api/search?q={token}", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["source"] == "event"
    assert items[0]["patient_id"] == pid
    assert token in items[0]["title"]


async def test_search_scoped_by_clinic(client: AsyncClient, auth_headers):
    pid = (
        await client.post("/api/patients", headers=auth_headers, json={"name": "Hidden P"})
    ).json()["id"]
    token = "zanzibarsecret"
    await client.post(
        f"/api/patients/{pid}/events",
        headers=auth_headers,
        json={"type": "note", "payload": {"text": f"note about {token}"}},
    )
    other = await client.post(
        "/api/auth/signup",
        json={"clinic_name": "Other", "name": "Dr X", "phone": "6666666666", "password": "secret123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['token']}"}
    resp = await client.get(f"/api/search?q={token}", headers=other_headers)
    assert resp.json() == []
