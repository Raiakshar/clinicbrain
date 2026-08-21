import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _patient(client: AsyncClient, headers) -> int:
    resp = await client.post("/api/patients", headers=headers, json={"name": "Timeline P"})
    return resp.json()["id"]


async def test_add_and_list_note_ordered(client: AsyncClient, auth_headers):
    pid = await _patient(client, auth_headers)
    r1 = await client.post(
        f"/api/patients/{pid}/events",
        headers=auth_headers,
        json={"type": "note", "payload": {"text": "first visit note"}, "event_date": "2026-01-10"},
    )
    assert r1.status_code == 200
    r2 = await client.post(
        f"/api/patients/{pid}/events",
        headers=auth_headers,
        json={"type": "note", "payload": {"text": "second newer note"}, "event_date": "2026-03-01"},
    )
    assert r2.status_code == 200
    events = (await client.get(f"/api/patients/{pid}/events", headers=auth_headers)).json()
    texts = [e["payload"]["text"] for e in events]
    assert texts == ["second newer note", "first visit note"]


async def test_event_requires_valid_type(client: AsyncClient, auth_headers):
    pid = await _patient(client, auth_headers)
    resp = await client.post(
        f"/api/patients/{pid}/events",
        headers=auth_headers,
        json={"type": "nonsense", "payload": {}},
    )
    assert resp.status_code == 422
