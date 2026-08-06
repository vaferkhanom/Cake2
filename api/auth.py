"""Telegram Mini App initData validation — HMAC-SHA256 per official docs.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

The client sends the raw `Telegram.WebApp.initData` query string in the
`Authorization: tma <initData>` header. We verify the `hash` field:
    secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
    data_check_string = sorted fields (excluding hash) joined with "\\n"
    expected_hash = hex(HMAC_SHA256(key=secret_key, msg=data_check_string))
Also enforce auth_date freshness to prevent replay of old data.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import HTTPException, Request

from src.config import settings


@dataclass
class TelegramUser:
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    language_code: str = ""
    is_premium: bool = False
    photo_url: str = ""


def _compute_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _compute_hash(data_check_string: str, secret_key: bytes) -> str:
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def parse_init_data(init_data: str) -> dict:
    """Parse the initData query string into a dict of RAW values.

    Values are NOT URL-decoded here: Telegram computes the data_check_string
    hash over the raw (still-encoded) values, so we must keep them as-is.
    Decoding happens later in extract_user() for the fields we read.
    """
    out: dict[str, str] = {}
    for pair in init_data.split("&"):
        if not pair:
            continue
        key, _, value = pair.partition("=")
        out[key] = value
    return out


def validate_init_data(init_data: str, bot_token: str, max_age: int | None = None) -> dict:
    """Validate initData. Returns the parsed data dict or raises ValueError."""
    if not init_data:
        raise ValueError("initData is empty")

    data = parse_init_data(init_data)
    received_hash = data.get("hash")
    if not received_hash:
        raise ValueError("missing hash")

    # data_check_string: all fields except hash, sorted alphabetically,
    # key=value joined with "\n"
    items = [(k, v) for k, v in data.items() if k != "hash"]
    items.sort(key=lambda kv: kv[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)

    secret_key = _compute_secret_key(bot_token)
    expected_hash = _compute_hash(data_check_string, secret_key)

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("hash mismatch")

    if max_age is not None:
        try:
            auth_date = int(data.get("auth_date", "0"))
        except (TypeError, ValueError):
            auth_date = 0
        if time.time() - auth_date > max_age:
            raise ValueError("initData is too old")

    return data


def extract_user(data: dict) -> TelegramUser:
    """Parse the `user` JSON field into a TelegramUser."""
    raw = data.get("user", "{}")
    try:
        obj = json.loads(urllib.parse.unquote_plus(raw))
    except (TypeError, json.JSONDecodeError):
        obj = {}
    return TelegramUser(
        id=int(obj.get("id", 0)),
        first_name=obj.get("first_name", ""),
        last_name=obj.get("last_name", ""),
        username=obj.get("username", ""),
        language_code=obj.get("language_code", ""),
        is_premium=bool(obj.get("is_premium", False)),
        photo_url=obj.get("photo_url", ""),
    )


async def get_telegram_user(request: Request) -> TelegramUser:
    """FastAPI dependency: validate Authorization header and return the user."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    init_data = header[4:].strip()

    try:
        data = validate_init_data(
            init_data,
            settings.BOT_TOKEN,
            max_age=settings.INIT_DATA_MAX_AGE_SECONDS,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid initData: {e}")

    user = extract_user(data)
    if user.id <= 0:
        raise HTTPException(status_code=401, detail="Invalid user in initData")
    return user
