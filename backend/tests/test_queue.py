import pytest
from httpx import AsyncClient

from app.config import settings
from app.workers import tasks as worker_tasks

pytestmark = pytest.mark.asyncio

FAILING_PHONE = "0009999999"
OK_PHONE = "9812345678"


async def _patient(client: AsyncClient, headers, phone: str, consent: bool = True) -> int:
    resp = await client.post(
        "/api/patients",
        headers=headers,
        json={"name": f"Q Patient {phone}", "phone": phone, "whatsapp_consent": consent},
    )
    return resp.json()["id"]


def _force_fail(monkeypatch):
    async def fail_send(self, to_phone, message):
        from app.services.whatsapp import WhatsAppError

        raise WhatsAppError("simulated outage")

    monkeypatch.setattr(settings, "whatsapp_provider", "meta")
    from app.services import whatsapp as wa_mod
    monkeypatch.setattr(wa_mod.MetaCloudProvider, "send", fail_send)


async def test_check_in_assigns_sequential_numbers(client, auth_headers):
    p1 = await _patient(client, auth_headers, OK_PHONE)
    p2 = await _patient(client, auth_headers, "9812345679")
    t1 = (await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": p1})).json()
    t2 = (await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": p2})).json()
    assert t1["number"] == 1 and t2["number"] == 2

    dup = (await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": p1})).json()
    assert dup["id"] == t1["id"], "re-check-in returns existing active token"

    queue_list = (await client.get("/api/queue/today", headers=auth_headers)).json()
    assert [q["number"] for q in queue_list] == [1, 2]


async def test_call_and_complete_flow_with_messages(client, auth_headers, stub_task):
    pid = await _patient(client, auth_headers, OK_PHONE)
    token = (
        await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": pid})
    ).json()

    called = await client.post(f"/api/queue/{token['id']}/call", headers=auth_headers)
    assert called.json()["status"] == "in_consult"

    conflict = await client.post(
        "/api/queue/check-in", headers=auth_headers, json={"patient_id": pid + 100}
    )
    assert conflict.status_code == 404

    done = await client.post(f"/api/queue/{token['id']}/complete", headers=auth_headers)
    assert done.json()["status"] == "done"

    log = (await client.get("/api/queue/whatsapp-log", headers=auth_headers)).json()
    templates = {entry["template"] for entry in log}
    assert {"token_confirmation", "your_turn"}.issubset(templates)
    for entry in log:
        await worker_tasks._send_whatsapp(entry["id"], 0)
    log = (await client.get("/api/queue/whatsapp-log", headers=auth_headers)).json()
    assert all(e["status"] == "sent" for e in log)


async def test_second_call_blocked_while_in_consult(client, auth_headers):
    p1 = await _patient(client, auth_headers, OK_PHONE)
    p2 = await _patient(client, auth_headers, "9812345679")
    t1 = (
        await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": p1})
    ).json()
    t2 = (
        await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": p2})
    ).json()
    await client.post(f"/api/queue/{t1['id']}/call", headers=auth_headers)
    second = await client.post(f"/api/queue/{t2['id']}/call", headers=auth_headers)
    assert second.status_code == 409


async def test_no_consent_skips_whatsapp(client, auth_headers):
    pid = await _patient(client, auth_headers, OK_PHONE, consent=False)
    await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": pid})
    log = (await client.get("/api/queue/whatsapp-log", headers=auth_headers)).json()
    assert all(entry["patient_name"] != f"Q Patient {OK_PHONE}" for entry in log) or log == []


async def test_whatsapp_retry_then_failed_visible_on_dashboard(client, auth_headers, monkeypatch, stub_task):
    _force_fail(monkeypatch)
    pid = await _patient(client, auth_headers, FAILING_PHONE)
    await client.post("/api/queue/check-in", headers=auth_headers, json={"patient_id": pid})

    logs = (await client.get("/api/queue/whatsapp-log?status=retrying", headers=auth_headers)).json()
    entry = next(e for e in logs if e["template"] == "token_confirmation")
    log_id = entry["id"]

    from app.services.whatsapp import WhatsAppError

    for attempt in range(4):
        if attempt < 3:
            with pytest.raises(WhatsAppError):
                await worker_tasks._send_whatsapp(log_id, attempt)
        else:
            await worker_tasks._send_whatsapp(log_id, attempt)

    failed = (
        await client.get("/api/queue/whatsapp-log?status=failed", headers=auth_headers)
    ).json()
    match = next(e for e in failed if e["id"] == log_id)
    assert match["retries"] == 4
    assert "simulated outage" in match["error"]


async def test_followup_reminder_sent_day_before_only_once(client, auth_headers, db_session, monkeypatch, stub_task):
    import datetime as dt


    pid = await _patient(client, auth_headers, OK_PHONE)
    tomorrow = dt.date.today() + dt.timedelta(days=1)

    from app.models import TimelineEvent

    async with db_session() as db:
        db.add(
            TimelineEvent(
                patient_id=pid,
                type="prescription",
                event_date=tomorrow,
                payload={"followup_date": tomorrow.isoformat(), "summary": "Rx follow-up"},
            )
        )
        await db.commit()

    await worker_tasks._followup_reminders()
    await worker_tasks._followup_reminders()

    logs = (await client.get("/api/queue/whatsapp-log", headers=auth_headers)).json()
    reminders = [e for e in logs if e["template"] == "followup_reminder"]
    assert len(reminders) == 1
    assert tomorrow.isoformat() in reminders[0]["body"]
