import pytest
from httpx import AsyncClient

from app.workers import tasks as worker_tasks

pytestmark = pytest.mark.asyncio

IMAGE = b"\x89PNG\r\n\x1a\n" + b"x" * 64


async def _lab_doc(client: AsyncClient, headers) -> int:
    pid = (
        await client.post("/api/patients", headers=headers, json={"name": "Lab Patient"})
    ).json()["id"]
    resp = await client.post(
        f"/api/patients/{pid}/documents",
        headers=headers,
        files={"file": ("report.png", IMAGE, "image/png")},
    )
    assert resp.status_code == 200
    doc_id = (
        await client.get("/api/documents?status=pending", headers=headers)
    ).json()[0]["id"]
    await worker_tasks._run(doc_id, "full")
    return pid, doc_id


async def test_lab_auto_chain_populates_draft_rows(
    client, auth_headers, stub_task, monkeypatch
):
    from app.services.extraction import fake as fake_mod

    async def lab_extract(self, image, mime):
        return fake_mod.ExtractedDocument(
            document_type="lab",
            summary="Lab panel",
            content_text="Hemoglobin 10.2 g/dL (13-17)",
        )

    monkeypatch.setattr(fake_mod.FakeProvider, "extract", lab_extract)
    pid = (
        await client.post("/api/patients", headers=auth_headers, json={"name": "Chain P"})
    ).json()["id"]
    resp = await client.post(
        f"/api/patients/{pid}/documents",
        headers=auth_headers,
        files={"file": ("panel.png", IMAGE, "image/png")},
    )
    assert resp.status_code == 200
    doc_id = (
        await client.get("/api/documents?status=pending", headers=auth_headers)
    ).json()[0]["id"]

    await worker_tasks._run(doc_id, "full")

    doc = next(
        d for d in (await client.get("/api/documents", headers=auth_headers)).json()
        if d["id"] == doc_id
    )
    assert len(doc["extracted"]["labs"]) == 4
    assert doc["extracted"]["labs"][0]["test_name"] == "Hemoglobin"


async def test_confirm_labs_creates_results_event_and_trend(client, auth_headers, stub_task):
    pid, doc_id = await _lab_doc(client, auth_headers)
    resp = await client.post(
        f"/api/documents/{doc_id}/confirm-labs",
        headers=auth_headers,
        json={
            "rows": [
                {
                    "test_name": "Hemoglobin",
                    "value": "10.2",
                    "unit": "g/dL",
                    "ref_low": "13.0",
                    "ref_high": "17.0",
                    "taken_at": "2026-08-20",
                },
                {
                    "test_name": "Fasting Glucose",
                    "value": "148",
                    "unit": "mg/dL",
                    "ref_low": "70",
                    "ref_high": "100",
                },
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json()["inserted"] == 2

    labs = (await client.get(f"/api/patients/{pid}/labs", headers=auth_headers)).json()
    by_test = {l["test_name"]: l for l in labs}
    assert by_test["Hemoglobin"]["flag"] == "low"
    assert by_test["Fasting Glucose"]["flag"] == "high"

    events = (await client.get(f"/api/patients/{pid}/events", headers=auth_headers)).json()
    lab_events = [e for e in events if e["type"] == "lab"]
    assert len(lab_events) == 1
    assert "Hemoglobin" in lab_events[0]["payload"]["content_text"]

    trend = (
        await client.get(
            f"/api/patients/{pid}/labs/trend",
            headers=auth_headers,
            params={"test_name": "Hemoglobin"},
        )
    ).json()
    assert [t["value"] for t in trend] == [10.2]


async def test_confirm_labs_rejects_unparseable_value(client, auth_headers, stub_task):
    _pid, doc_id = await _lab_doc(client, auth_headers)
    resp = await client.post(
        f"/api/documents/{doc_id}/confirm-labs",
        headers=auth_headers,
        json={"rows": [{"test_name": "Weird Test", "value": "not-a-number"}]},
    )
    assert resp.status_code == 422
    assert "Row 1" in resp.json()["detail"]


async def test_confirm_labs_missing_refs_flags_review(client, auth_headers, stub_task):
    pid, doc_id = await _lab_doc(client, auth_headers)
    await client.post(
        f"/api/documents/{doc_id}/confirm-labs",
        headers=auth_headers,
        json={"rows": [{"test_name": "Custom Panel X", "value": "42"}]},
    )
    labs = (await client.get(f"/api/patients/{pid}/labs", headers=auth_headers)).json()
    assert labs[0]["flag"] == "review"


async def test_extract_labs_rerun_endpoint(client, auth_headers, stub_task):
    _pid, doc_id = await _lab_doc(client, auth_headers)
    resp = await client.post(f"/api/documents/{doc_id}/extract-labs", headers=auth_headers)
    assert resp.json() == {"status": "queued"}
