"""Integration tests for the FastAPI Mini App API (api/main.py).

Uses an in-memory SQLite DB via monkeypatched env vars, real initData signing
against the test BOT_TOKEN, and the full domain layer.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.parse
from pathlib import Path

import pytest

# Configure env BEFORE importing app/session modules
os.environ["BOT_TOKEN"] = "123456:TEST-BOT-TOKEN"
os.environ["DB_PATH"] = "/tmp/test_api_promise_bot.db"
os.environ.pop("DATABASE_URL", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Remove any stale test DB
try:
    Path("/tmp/test_api_promise_bot.db").unlink()
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient

from api.auth import _compute_hash, _compute_secret_key
from api.main import app
from src.database import session as db
from src.database.models import Promise, PromiseStatus, TargetType, User

BOT_TOKEN = os.environ["BOT_TOKEN"]
USER_ID = 111111111
OTHER_ID = 222222222


@pytest.fixture()
def client():
    # Fresh DB per test
    try:
        Path("/tmp/test_api_promise_bot.db").unlink()
    except FileNotFoundError:
        pass
    # Reset engine so a new one is created for the fresh DB file
    db._engine = None
    db._async_session_maker = None
    with TestClient(app) as c:
        yield c
    db._engine = None
    db._async_session_maker = None


def _init_data(user_id: int, first_name: str = "Ali", username: str = "ali") -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        # URL-encode the user JSON exactly like Telegram's WebApp does
        "user": urllib.parse.quote_plus(
            '{"id": %d, "first_name": "%s", "last_name": "", "username": "%s", "language_code": "fa"}'
            % (user_id, first_name, username)
        ),
    }
    items = sorted((k, v) for k, v in payload.items())
    dcs = "\n".join(f"{k}={v}" for k, v in items)
    secret = _compute_secret_key(BOT_TOKEN)
    payload["hash"] = _compute_hash(dcs, secret)
    return "&".join(f"{k}={v}" for k, v in payload.items())


def _headers(user_id: int = USER_ID, first_name: str = "Ali", username: str = "ali") -> dict:
    return {"Authorization": f"tma {_init_data(user_id, first_name, username)}"}


# ── Auth ────────────────────────────────────────────────────────────────────

def test_me_requires_auth(client):
    r = client.get("/api/me")
    assert r.status_code == 401


def test_me_creates_user(client):
    r = client.get("/api/me", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["telegram_id"] == USER_ID
    assert body["user"]["score"] == 0
    assert body["stats"]["total_given"] == 0


def test_me_rejects_bad_token(client):
    payload = _init_data(USER_ID).replace("tma ", "tma x")
    r = client.get("/api/me", headers={"Authorization": f"tma {_init_data(USER_ID)[:20]}bad"})
    assert r.status_code == 401


def test_me_rejects_expired(client):
    payload = _init_data(USER_ID)
    data = dict(x.split("=", 1) for x in payload.split("&"))
    data["auth_date"] = str(int(time.time()) - 100000)
    items = sorted((k, v) for k, v in data.items())
    dcs = "\n".join(f"{k}={v}" for k, v in items)
    secret = _compute_secret_key(BOT_TOKEN)
    data["hash"] = _compute_hash(dcs, secret)
    qs = "&".join(f"{k}={v}" for k, v in data.items())
    r = client.get("/api/me", headers={"Authorization": f"tma {qs}"})
    assert r.status_code == 401


# ── Promises ────────────────────────────────────────────────────────────────

def test_create_self_promise(client):
    r = client.post("/api/promises", headers=_headers(), json={
        "content": "قول می‌دم هر روز ورزش کنم",
        "target_type": "self",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "confirmed"
    assert body["is_giver"] is True
    assert body["content"] == "قول می‌دم هر روز ورزش کنم"


def test_list_self_promises(client):
    client.post("/api/promises", headers=_headers(), json={"content": "c1", "target_type": "self"})
    client.post("/api/promises", headers=_headers(), json={"content": "c2", "target_type": "self"})
    r = client.get("/api/promises", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_friend_promise_creates_stub_user(client):
    r = client.post("/api/promises", headers=_headers(), json={
        "content": "قول می‌دم بهت کتاب بدم",
        "target_type": "friend",
        "receiver_username": "reza",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["target_type"] == "friend"
    assert body["receiver_name"] == "@reza"


def test_friend_promise_requires_username(client):
    r = client.post("/api/promises", headers=_headers(), json={
        "content": "x", "target_type": "friend",
    })
    assert r.status_code == 400


def _register(client, user_id, first_name, username):
    """Register a REAL user (positive telegram_id) via /api/me."""
    r = client.get("/api/me", headers=_headers(user_id, first_name, username))
    assert r.status_code == 200


def test_respond_accept_flow(client):
    # receiver is a real user who has opened the app before
    _register(client, OTHER_ID, "Reza", "reza")
    # giver creates friend promise
    r = client.post("/api/promises", headers=_headers(USER_ID, "Ali", "ali"), json={
        "content": "قول", "target_type": "friend", "receiver_username": "reza",
    })
    pid = r.json()["id"]
    # other user (the receiver) accepts
    r = client.post(f"/api/promises/{pid}/respond", headers=_headers(OTHER_ID, "Reza", "reza"), json={"action": "accept"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # status now confirmed
    r = client.get(f"/api/promises/{pid}", headers=_headers(USER_ID))
    assert r.json()["status"] == "confirmed"


def test_respond_reject_deletes(client):
    _register(client, OTHER_ID, "Reza", "reza")
    r = client.post("/api/promises", headers=_headers(USER_ID, "Ali", "ali"), json={
        "content": "قول", "target_type": "friend", "receiver_username": "reza",
    })
    pid = r.json()["id"]
    r = client.post(f"/api/promises/{pid}/respond", headers=_headers(OTHER_ID, "Reza", "reza"), json={"action": "reject"})
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    r = client.get(f"/api/promises/{pid}", headers=_headers(USER_ID))
    assert r.status_code == 404


def test_full_lifecycle_claim_confirm(client):
    # both users must exist in DB for scoring to apply
    _register(client, OTHER_ID, "Reza", "reza")
    _register(client, USER_ID, "Ali", "ali")
    r = client.post("/api/promises", headers=_headers(USER_ID, "Ali", "ali"), json={
        "content": "قول", "target_type": "friend", "receiver_username": "reza",
    })
    pid = r.json()["id"]
    client.post(f"/api/promises/{pid}/respond", headers=_headers(OTHER_ID, "Reza", "reza"), json={"action": "accept"})

    r = client.post(f"/api/promises/{pid}/claim-done", headers=_headers(USER_ID))
    assert r.json()["status"] == "claimed_done"

    r = client.post(f"/api/promises/{pid}/confirm-done", headers=_headers(OTHER_ID))
    assert r.json()["status"] == "done"

    # giver score should be incremented
    r = client.get("/api/me", headers=_headers(USER_ID))
    assert r.json()["user"]["score"] >= 10


def test_actions_require_role(client):
    _register(client, OTHER_ID, "Reza", "reza")
    r = client.post("/api/promises", headers=_headers(USER_ID, "Ali", "ali"), json={
        "content": "قول", "target_type": "friend", "receiver_username": "reza",
    })
    pid = r.json()["id"]
    # receiver tries to claim done — should fail
    r = client.post(f"/api/promises/{pid}/claim-done", headers=_headers(OTHER_ID))
    assert r.status_code == 400


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
