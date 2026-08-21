import pytest

pytestmark = pytest.mark.asyncio

SIGNUP = {
    "clinic_name": "Sunrise Clinic",
    "name": "Dr Mehta",
    "phone": "7777777777",
    "password": "secret123",
}


async def test_signup_returns_token_and_user(client):
    resp = await client.post("/api/auth/signup", json=SIGNUP)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["user"]["role"] == "doctor"
    assert body["user"]["clinic_id"] > 0


async def test_duplicate_phone_conflict(client):
    await client.post("/api/auth/signup", json=SIGNUP)
    resp = await client.post("/api/auth/signup", json={**SIGNUP, "clinic_name": "Another"})
    assert resp.status_code == 409


async def test_login_success(client):
    await client.post("/api/auth/signup", json=SIGNUP)
    resp = await client.post("/api/auth/login", json={"phone": SIGNUP["phone"], "password": SIGNUP["password"]})
    assert resp.status_code == 200
    assert resp.json()["token"]


async def test_login_wrong_password(client):
    await client.post("/api/auth/signup", json=SIGNUP)
    resp = await client.post("/api/auth/login", json={"phone": SIGNUP["phone"], "password": "wrong"})
    assert resp.status_code == 401


async def test_me_endpoints_require_auth(client):
    resp = await client.get("/api/patients")
    assert resp.status_code == 401
