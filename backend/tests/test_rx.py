import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

OK_PHONE = "9811112222"


async def _patient(client: AsyncClient, headers, allergies: list[str] | None = None) -> int:
    resp = await client.post(
        "/api/patients",
        headers=headers,
        json={"name": "Rx Patient", "phone": OK_PHONE},
    )
    pid = resp.json()["id"]
    if allergies is not None:
        await client.put(f"/api/patients/{pid}/allergies", headers=headers, json={"allergies": allergies})
    return pid


def _item(drug: str, dose: float = 500, freq: int = 3) -> dict:
    return {"drug_name": drug, "dose_mg": dose, "frequency_per_day": freq}


async def test_drug_autocomplete(client, auth_headers):
    rows = (await client.get("/api/drugs", params={"q": "amox"}, headers=auth_headers)).json()
    assert any(r["name"] == "Amoxicillin" for r in rows)
    assert all("max_daily_dose_mg" in r for r in rows)


async def test_allergy_hard_block_rejects_save(client, auth_headers):
    pid = await _patient(client, auth_headers, allergies=["penicillin"])
    report = (
        await client.post(
            f"/api/patients/{pid}/check-rx",
            headers=auth_headers,
            json={"items": [_item("Amoxicillin")]},
        )
    ).json()
    assert any(b.startswith("ALLERGY") for b in report["blocks"])

    save = await client.post(
        f"/api/patients/{pid}/prescriptions",
        headers=auth_headers,
        json={"items": [_item("Amoxicillin")], "acknowledged_warnings": True},
    )
    assert save.status_code == 400
    assert "ALLERGY" in str(save.json())


async def test_class_level_allergy_matches_sulfa_drug(client, auth_headers):
    pid = await _patient(client, auth_headers, allergies=["sulfa"])
    report = (
        await client.post(
            f"/api/patients/{pid}/check-rx",
            headers=auth_headers,
            json={"items": [_item("Cotrimoxazole", 960, 2)]},
        )
    ).json()
    assert any(b.startswith("ALLERGY") for b in report["blocks"])


async def test_max_dose_warning_requires_ack_then_saves(client, auth_headers):
    pid = await _patient(client, auth_headers)
    items = [_item("Paracetamol", 1000, 6)]
    first = await client.post(
        f"/api/patients/{pid}/prescriptions", headers=auth_headers, json={"items": items}
    )
    assert first.status_code == 409
    assert any(w.startswith("MAX DOSE") for w in first.json()["detail"]["warnings"])

    saved = await client.post(
        f"/api/patients/{pid}/prescriptions",
        headers=auth_headers,
        json={"items": items, "acknowledged_warnings": True},
    )
    assert saved.status_code == 200
    rx_id = saved.json()["id"]
    detail = (await client.get(f"/api/patients/{pid}/prescriptions", headers=auth_headers)).json()
    match = next(rx for rx in detail if rx["id"] == rx_id)
    assert match["items"][0]["drug_name"] == "Paracetamol"

    events = (await client.get(f"/api/patients/{pid}/events", headers=auth_headers)).json()
    assert any(e["type"] == "prescription" and "Paracetamol" in e["payload"].get("summary", "") for e in events)


async def test_interaction_warning_within_same_rx(client, auth_headers):
    pid = await _patient(client, auth_headers)
    items = [_item("Warfarin", 5, 1), _item("Aspirin", 75, 1)]
    report = (
        await client.post(f"/api/patients/{pid}/check-rx", headers=auth_headers, json={"items": items})
    ).json()
    assert any("INTERACTION" in w and "Aspirin + Warfarin" in w for w in report["warnings"])


async def test_cross_prescription_interaction_with_history(client, auth_headers):
    pid = await _patient(client, auth_headers)
    saved = await client.post(
        f"/api/patients/{pid}/prescriptions",
        headers=auth_headers,
        json={"items": [_item("Omeprazole", 20, 1)]},
    )
    assert saved.status_code == 200
    report = (
        await client.post(
            f"/api/patients/{pid}/check-rx",
            headers=auth_headers,
            json={"items": [_item("Clopidogrel", 75, 1)]},
        )
    ).json()
    assert any("existing medication" in w and "Clopidogrel + Omeprazole" in w for w in report["warnings"])


async def test_unknown_drug_warns_but_saves_clean(client, auth_headers):
    pid = await _patient(client, auth_headers)
    report = (
        await client.post(
            f"/api/patients/{pid}/check-rx",
            headers=auth_headers,
            json={"items": [{"drug_name": "Unknown Herb X", "dose_mg": 10, "frequency_per_day": 1}]},
        )
    ).json()
    assert any("not in reference list" in w for w in report["warnings"])
    assert report["blocks"] == []


async def test_followup_date_flows_to_timeline_payload(client, auth_headers):
    import datetime as dt

    pid = await _patient(client, auth_headers)
    followup = dt.date.today() + dt.timedelta(days=7)
    saved = await client.post(
        f"/api/patients/{pid}/prescriptions",
        headers=auth_headers,
        json={"items": [_item("Metformin", 500, 2)], "followup_date": followup.isoformat()},
    )
    assert saved.status_code == 200
    events = (await client.get(f"/api/patients/{pid}/events", headers=auth_headers)).json()
    event = next(e for e in events if e["type"] == "prescription")
    assert event["payload"]["followup_date"] == followup.isoformat()


async def test_allergies_update_roundtrip(client, auth_headers):
    pid = await _patient(client, auth_headers)
    resp = await client.put(
        f"/api/patients/{pid}/allergies", headers=auth_headers, json={"allergies": ["nsaid", "penicillin"]}
    )
    assert resp.json()["allergies"] == ["nsaid", "penicillin"]
