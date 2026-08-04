"""SQLAlchemy ORM models for Promise Bot."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, Enum, Boolean, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import jdatetime


class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────

class TargetType(str, enum.Enum):
    SELF = "self"
    FRIEND = "friend"


class PromiseStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CLAIMED_DONE = "claimed_done"    # Giver claims done, waiting for receiver confirmation
    DONE = "done"                    # Receiver confirmed done
    DISPUTED = "disputed"            # Receiver disputed the claim
    BROKEN = "broken"                # Giver admitted broken (no confirmation needed)
    EXPIRED = "expired"              # Deadline passed without resolution


# ── User Model ─────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    has_started_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Scoring fields
    score: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    promises_given: Mapped[List["Promise"]] = relationship(
        "Promise", back_populates="giver", foreign_keys="Promise.giver_id"
    )
    promises_received: Mapped[List["Promise"]] = relationship(
        "Promise", back_populates="receiver", foreign_keys="Promise.receiver_id"
    )

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name or str(self.telegram_id)

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} username={self.username}>"


# ── Promise Model ──────────────────────────────────────

class Promise(Base):
    __tablename__ = "promises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    promise_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)  # Human-friendly ID
    content: Mapped[str] = mapped_column(Text, nullable=False)
    giver_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False
    )
    receiver_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=True
    )
    target_type: Mapped[TargetType] = mapped_column(
        Enum(TargetType, native_enum=False), nullable=False
    )
    status: Mapped[PromiseStatus] = mapped_column(
        Enum(PromiseStatus, native_enum=False),
        nullable=False,
        default=PromiseStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Deadline and tracking fields
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_done_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Phase 4: For edit-message flow in claim/confirm/dispute
    giver_claim_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    giver_claim_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Relationships
    giver: Mapped["User"] = relationship(
        "User", back_populates="promises_given", foreign_keys=[giver_id]
    )
    receiver: Mapped[Optional["User"]] = relationship(
        "User", back_populates="promises_received", foreign_keys=[receiver_id]
    )

    @property
    def jalali_created_at(self) -> str:
        j_dt = jdatetime.datetime.fromtimestamp(self.created_at.timestamp())
        return j_dt.strftime("%Y/%m/%d ساعت %H:%M")

    @property
    def status_emoji(self) -> str:
        mapping = {
            PromiseStatus.PENDING: "⏳",
            PromiseStatus.CONFIRMED: "✅",
            PromiseStatus.REJECTED: "❌",
            PromiseStatus.CLAIMED_DONE: "⏳",
            PromiseStatus.DONE: "🏆",
            PromiseStatus.DISPUTED: "⚠️",
            PromiseStatus.BROKEN: "💔",
            PromiseStatus.EXPIRED: "⏰",
        }
        return mapping.get(self.status, "")

    @property
    def status_text(self) -> str:
        mapping = {
            PromiseStatus.PENDING: "در انتظار تایید",
            PromiseStatus.CONFIRMED: "تایید شده",
            PromiseStatus.REJECTED: "رد شده",
            PromiseStatus.CLAIMED_DONE: "در انتظار تایید طرف مقابل",
            PromiseStatus.DONE: "انجام شده",
            PromiseStatus.DISPUTED: "مخالفیت شده",
            PromiseStatus.BROKEN: "نقض شده",
            PromiseStatus.EXPIRED: "منقضی شده",
        }
        return mapping.get(self.status, "")

    @property
    def status_display(self) -> str:
        return f"{self.status_emoji} {self.status_text}"

    def __repr__(self) -> str:
        return f"<Promise id={self.id} status={self.status}>"