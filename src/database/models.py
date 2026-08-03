import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, Enum, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import jdatetime

class Base(DeclarativeBase):
    pass

class TargetType(str, enum.Enum):
    SELF = "self"
    FRIEND = "friend"

class PromiseStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DONE = "done"
    BROKEN = "broken"

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    has_started_bot: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    given_promises: Mapped[List["Promise"]] = relationship(
        "Promise", foreign_keys="Promise.giver_id", back_populates="giver"
    )
    received_promises: Mapped[List["Promise"]] = relationship(
        "Promise", foreign_keys="Promise.receiver_id", back_populates="receiver"
    )

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name or str(self.telegram_id)

class Promise(Base):
    __tablename__ = "promises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    promise_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)  # Human-friendly ID, nullable for migration
    content: Mapped[str] = mapped_column(Text, nullable=False)
    giver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    receiver_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=True)
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType), nullable=False)
    status: Mapped[PromiseStatus] = mapped_column(Enum(PromiseStatus), default=PromiseStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    giver: Mapped["User"] = relationship("User", foreign_keys=[giver_id], back_populates="given_promises")
    receiver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[receiver_id], back_populates="received_promises")

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
            PromiseStatus.DONE: "🏆",
            PromiseStatus.BROKEN: "💔",
        }
        return mapping.get(self.status, "")

    @property
    def status_text(self) -> str:
        mapping = {
            PromiseStatus.PENDING: "در انتظار تایید",
            PromiseStatus.CONFIRMED: "تایید شده",
            PromiseStatus.REJECTED: "رد شده",
            PromiseStatus.DONE: "انجام شده",
            PromiseStatus.BROKEN: "نقض شده",
        }
        return mapping.get(self.status, "")

    @property
    def status_display(self) -> str:
        return f"{self.status_emoji} {self.status_text}"