"""Tests for Telegram initData validation (api/auth.py)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.auth import (
    _compute_hash,
    _compute_secret_key,
    extract_user,
    parse_init_data,
    validate_init_data,
)

BOT_TOKEN = "123456:TEST-BOT-TOKEN"


def _sign(data: dict, token: str = BOT_TOKEN) -> dict:
    """Sign a dict like Telegram does."""
    items = sorted((k, v) for k, v in data.items())
    dcs = "\n".join(f"{k}={v}" for k, v in items)
    secret = _compute_secret_key(token)
    data["hash"] = _compute_hash(dcs, secret)
    return data


def test_validate_ok():
    data = _sign({"auth_date": str(int(time.time())), "user": '{"id": 42, "first_name": "Ali"}'})
    qs = "&".join(f"{k}={v}" for k, v in data.items())
    out = validate_init_data(qs, BOT_TOKEN)
    assert out["user"] == '{"id": 42, "first_name": "Ali"}'


def test_validate_wrong_token():
    data = _sign({"auth_date": str(int(time.time())), "user": "{}"})
    qs = "&".join(f"{k}={v}" for k, v in data.items())
    with pytest.raises(ValueError):
        validate_init_data(qs, "other:token")


def test_validate_tampered():
    data = _sign({"auth_date": str(int(time.time())), "user": '{"id": 42}'})
    data["user"] = '{"id": 43}'  # tamper after signing
    qs = "&".join(f"{k}={v}" for k, v in data.items())
    with pytest.raises(ValueError):
        validate_init_data(qs, BOT_TOKEN)


def test_validate_missing_hash():
    with pytest.raises(ValueError):
        validate_init_data("auth_date=123&user=%7B%7D", BOT_TOKEN)


def test_validate_expired():
    data = _sign({"auth_date": str(int(time.time()) - 100000), "user": "{}"})
    qs = "&".join(f"{k}={v}" for k, v in data.items())
    with pytest.raises(ValueError):
        validate_init_data(qs, BOT_TOKEN, max_age=3600)


def test_parse_init_data_handles_url_encoding():
    qs = "user=%7B%22id%22%3A%207%7D&auth_date=123"
    data = parse_init_data(qs)
    assert data["user"] == '{"id": 7}'


def test_extract_user():
    data = _sign({"auth_date": str(int(time.time())), "user": '{"id": 7, "username": "ali", "first_name": "Ali"}'})
    u = extract_user(data)
    assert u.id == 7
    assert u.username == "ali"
