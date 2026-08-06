"""Pydantic schemas for the Promise Bot Mini App API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PromiseOut(BaseModel):
    id: int
    promise_id: Optional[int] = None
    content: str
    giver_id: int
    receiver_id: Optional[int] = None
    target_type: Literal["self", "friend"]
    status: str
    deadline: Optional[datetime] = None
    created_at: datetime
    claimed_done_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Resolved display fields (computed for the UI)
    status_text: str = ""
    status_emoji: str = ""
    jalali_created_at: str = ""
    jalali_deadline: Optional[str] = None

    giver_name: str = ""
    receiver_name: str = ""
    is_giver: bool = False
    is_receiver: bool = False


class UserOut(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    full_name: str
    score: int = 0
    current_streak: int = 0
    display_name: str = ""
    created_at: Optional[datetime] = None


class MeOut(BaseModel):
    user: UserOut
    stats: dict


class PromiseCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    target_type: Literal["self", "friend"]
    receiver_username: Optional[str] = None  # for friend promises
    deadline: Optional[datetime] = None


class RespondIn(BaseModel):
    action: Literal["accept", "reject"]


class PromiseListOut(BaseModel):
    type: str
    page: int
    total: int
    total_pages: int
    items: list[PromiseOut]


class ApiError(BaseModel):
    detail: str
