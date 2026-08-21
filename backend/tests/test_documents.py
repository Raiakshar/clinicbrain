import pytest
from httpx import AsyncClient

from app.config import settings
from app.workers import tasks as worker_tasks


class StubTask:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def delay(self, document_id: str) -> None:
        self.calls.append(document_id)


@pytest.fixture
def stub_task(monkeypatch):
    stub = StubTask()
    monkeypatch.setattr(worker_tasks, "extract_document_task", stub)
    return stub

pytestmark = pytest.mark.asyncio

IMAGE = b"\x89PNG\r\n\x1a\n" + b"x" * 64


async def _upload(client: AsyncClient, headers) -> int:
    pid = (
        await client.post("/api/patients", headers=headers, json={"name": "Doc Patient"})
    ).json()["id"]
    resp = await client.post(
        f"/api/patients/{pid}/documents",
        headers=headers,
        files={"file": ("scan.png", IMAGE, "image/png")},
    )
    assert resp.status_code == 200
    return pid


async def test_upload_stores_and_enqueues(client, auth_headers, fake_storage, stub_task):
    pid = await _upload(client, auth_headers)
    assert stub_task.calls and stub_task.calls[0].isdigit()
    key = next(iter(fake_storage.objects))
    assert key.startswith(f"patients/{pid}/")


async def test_extraction_success_flow(client, auth_headers, db_session, stub_task):
    pid = await _upload(client, auth_headers)
    doc_id = (
        await client.get("/api/documents?status=pending", headers=auth_headers)
    ).json()[0]["id"]

    await worker_tasks._extract(doc_id)

    doc = (
        await client.get("/api/documents?status=needs_review", headers=auth_headers)
    ).json()[0]
    assert doc["extracted"]["summary"] == "Chest X-ray report"
    assert doc["ocr_text"].startswith("Impression")

    confirm = await client.post(
        f"/api/documents/{doc_id}/confirm",
        headers=auth_headers,
        json={
            "document_type": "report",
            "event_date": "2026-08-01",
            "summary": "Chest X-ray report",
            "content_text": doc["extracted"]["content_text"],
        },
    )
    assert confirm.status_code == 200
    events = (await client.get(f"/api/patients/{pid}/events", headers=auth_headers)).json()
    assert any(e["type"] == "document" and e["payload"]["document_id"] == doc_id for e in events)


async def test_extraction_failure_marks_failed_and_retry(
    client, auth_headers, fake_storage, monkeypatch, stub_task
):
    monkeypatch.setattr(settings, "extraction_provider", "gpt")
    await _upload(client, auth_headers)
    doc_id = (
        await client.get("/api/documents?status=pending", headers=auth_headers)
    ).json()[0]["id"]

    await worker_tasks._extract(doc_id)
    failed = (await client.get("/api/documents?status=failed", headers=auth_headers)).json()
    assert failed[0]["error"] is not None

    stub_task.calls.clear()
    resp = await client.post(f"/api/documents/{doc_id}/retry", headers=auth_headers)
    assert resp.json() == {"status": "pending"}
    assert stub_task.calls == [str(doc_id)]


async def test_reject_deletes_document(client, auth_headers, fake_storage, stub_task):
    await _upload(client, auth_headers)
    doc_id = (
        await client.get("/api/documents?status=pending", headers=auth_headers)
    ).json()[0]["id"]
    resp = await client.post(f"/api/documents/{doc_id}/reject", headers=auth_headers)
    assert resp.status_code == 204
    remaining = (await client.get("/api/documents", headers=auth_headers)).json()
    assert remaining == []
