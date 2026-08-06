"""Shared domain actions for Promise Bot — the single source of truth for the
promise state machine.

Both the aiogram bot (src/handlers/promise.py) and the FastAPI Mini App backend
(api/) call into this module. Pure business logic: no aiogram, no HTTP, no
keyboards. All I/O is expressed through the ``notifier`` interface so this file
stays fully testable with plain SQLAlchemy sessions.

State machine (must stay identical to the bot's current behavior):

    PENDING -> CONFIRMED / REJECTED
    CONFIRMED -> CLAIMED_DONE / BROKEN
    CLAIMED_DONE -> DONE / DISPUTED
    DISPUTED -> DONE            (receiver resolves)
    (any open state) -> EXPIRED (deadline passed — periodic job, see bot.py TODO)

Scoring rules (src/services/scoring.py, unchanged):
    DONE (friend only): +10 base, +streak bonus (cap 10), +early bonus (max 10)
    BROKEN (friend only): -8, streak reset
    DISPUTED: -5 immediate penalty (receiver rejects claim)
    resolve-dispute -> DONE: -5 penalty cancelled, then full DONE scoring
    EXPIRED: -12, streak reset
    Self promises never score.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Promise, PromiseStatus, TargetType, User
from src.services.scoring import (
    apply_broken_score,
    apply_disputed_score,
    apply_done_score,
    apply_expired_score,
    resolve_dispute_to_done,
)

logger = logging.getLogger(__name__)

# ── Notifier protocol ────────────────────────────────────────────────────────
# The domain layer only declares WHAT to notify; transports implement it.
# The aiogram bot passes an adapter that sends Telegram messages; the FastAPI
# backend passes one that records outbox entries (or sends nothing and lets the
# bot pick up the change on the next /start / pending scan).


class PromiseNotifier(Protocol):
    """Interface for outbound user notifications."""

    async def on_promise_created(self, promise: Promise, giver_name: str, invite_link: str | None = None) -> None: ...
    async def on_promise_accepted(self, promise: Promise, acceptor_name: str) -> None: ...
    async def on_promise_rejected(self, promise_id: int, giver_id: int, content: str, rejector_name: str) -> None: ...
    async def on_claimed_done(self, promise: Promise, giver_name: str) -> None: ...
    async def on_confirm_done(self, promise: Promise, confirmer_name: str) -> None: ...
    async def on_disputed(self, promise: Promise, disputer_name: str) -> None: ...
    async def on_broken(self, promise: Promise) -> None: ...
    async def on_resolved(self, promise: Promise) -> None: ...
    async def on_expired(self, promise: Promise) -> None: ...


class NoopNotifier:
    """Default notifier that does nothing (used by tests / API)."""

    async def on_promise_created(self, promise: Promise, giver_name: str, invite_link: str | None = None) -> None: ...
    async def on_promise_accepted(self, promise: Promise, acceptor_name: str) -> None: ...
    async def on_promise_rejected(self, promise_id: int, giver_id: int, content: str, rejector_name: str) -> None: ...
    async def on_claimed_done(self, promise: Promise, giver_name: str) -> None: ...
    async def on_confirm_done(self, promise: Promise, confirmer_name: str) -> None: ...
    async def on_disputed(self, promise: Promise, disputer_name: str) -> None: ...
    async def on_broken(self, promise: Promise) -> None: ...
    async def on_resolved(self, promise: Promise) -> None: ...
    async def on_expired(self, promise: Promise) -> None: ...


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class ActionResult:
    ok: bool
    error: str | None = None
    promise: Promise | None = None
    deleted: bool = False
    details: dict = field(default_factory=dict)


# ── Errors ───────────────────────────────────────────────────────────────────

class DomainError(Exception):
    """Raised for invalid domain transitions. Callers translate to HTTP 400 / alert."""


# ── Lookup helpers ───────────────────────────────────────────────────────────

async def _load_promise(session: AsyncSession, promise_id: int) -> Promise | None:
    stmt = select(Promise).where(Promise.id == promise_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


# ── Create ───────────────────────────────────────────────────────────────────

async def create_promise(
    session: AsyncSession,
    *,
    giver_id: int,
    content: str,
    target_type: TargetType,
    receiver_id: int | None = None,
    deadline: datetime | None = None,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Create a promise.

    - target_type SELF   -> receiver_id = giver_id, status CONFIRMED immediately
    - target_type FRIEND -> status PENDING; receiver gets a notification
      (via notifier) and must accept/reject. If receiver is unknown to the bot
      yet, the caller is responsible for creating a stub user first (or the
      notifier returns an invite link in ``details``).
    """
    from src.database.session import create_promise as _create_promise_row

    content = (content or "").strip()
    if not content:
        return ActionResult(ok=False, error="متن قول نمی‌تونه خالی باشه")

    if target_type == TargetType.SELF:
        promise = await _create_promise_row(
            session,
            giver_id=giver_id,
            content=content,
            target_type=TargetType.SELF,
            receiver_id=giver_id,
            status=PromiseStatus.CONFIRMED,
            deadline=deadline,
        )
        await session.flush()
        if notifier:
            await notifier.on_promise_created(promise, giver_name=str(giver_id))
        return ActionResult(ok=True, promise=promise)

    # FRIEND
    if not receiver_id:
        return ActionResult(ok=False, error="گیرنده مشخص نشده")

    promise = await _create_promise_row(
        session,
        giver_id=giver_id,
        content=content,
        target_type=TargetType.FRIEND,
        receiver_id=receiver_id,
        status=PromiseStatus.PENDING,
        deadline=deadline,
    )
    await session.flush()
    if notifier:
        await notifier.on_promise_created(promise, giver_name=str(giver_id))
    return ActionResult(ok=True, promise=promise)


# ── Accept / reject ──────────────────────────────────────────────────────────

async def accept_promise(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Receiver accepts a PENDING promise -> CONFIRMED."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.receiver_id != actor_id:
        return ActionResult(ok=False, error="این دکمه برای شما نیست")
    if promise.status != PromiseStatus.PENDING:
        return ActionResult(ok=False, error="این قول در وضعیت قابل تایید نیست")

    promise.status = PromiseStatus.CONFIRMED
    await session.flush()
    if notifier:
        await notifier.on_promise_accepted(promise, acceptor_name=str(actor_id))
    return ActionResult(ok=True, promise=promise)


async def reject_promise(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Receiver rejects a PENDING promise -> record deleted (current bot behavior)."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.receiver_id != actor_id:
        return ActionResult(ok=False, error="این دکمه برای شما نیست")
    if promise.status != PromiseStatus.PENDING:
        return ActionResult(ok=False, error="این قول در وضعیت قابل رد نیست")

    giver_id = promise.giver_id
    content = promise.content
    await session.delete(promise)
    await session.flush()
    if notifier:
        # Promise is deleted from DB — notify with the essential fields
        await notifier.on_promise_rejected(
            promise_id=promise_id,
            giver_id=giver_id,
            content=content,
            rejector_name=str(actor_id),
        )
    return ActionResult(ok=True, deleted=True, promise=None)


# ── Claim done / broken (giver side) ─────────────────────────────────────────

async def claim_done(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Giver claims a CONFIRMED promise done -> CLAIMED_DONE."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.giver_id != actor_id:
        return ActionResult(ok=False, error="فقط قول‌دهنده می‌تونه ادعای انجام بده")
    if promise.status != PromiseStatus.CONFIRMED:
        return ActionResult(ok=False, error="فقط قول‌های تایید شده قابل ادعای انجام‌ان")

    promise.status = PromiseStatus.CLAIMED_DONE
    promise.claimed_done_at = datetime.now(timezone.utc)
    await session.flush()
    if notifier:
        await notifier.on_claimed_done(promise, giver_name=str(actor_id))
    return ActionResult(ok=True, promise=promise)


async def mark_broken(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Giver admits a CONFIRMED promise is broken -> BROKEN (no confirmation needed)."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.giver_id != actor_id:
        return ActionResult(ok=False, error="فقط قول‌دهنده می‌تونه وضعیت رو عوض کنه")
    if promise.status != PromiseStatus.CONFIRMED:
        return ActionResult(ok=False, error="فقط قول‌های تایید شده قابل ثبت نشدنش")

    promise.status = PromiseStatus.BROKEN
    promise.resolved_at = datetime.now(timezone.utc)
    await apply_broken_score(session, promise.giver_id, promise)
    await session.flush()
    if notifier:
        await notifier.on_broken(promise)
    return ActionResult(ok=True, promise=promise)


# ── Confirm done / dispute (receiver side) ───────────────────────────────────

async def confirm_done(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Receiver confirms a CLAIMED_DONE promise -> DONE + scoring."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.receiver_id != actor_id:
        return ActionResult(ok=False, error="فقط گیرنده قول می‌تونه تایید کنه")
    if promise.status != PromiseStatus.CLAIMED_DONE:
        return ActionResult(ok=False, error="این قول در وضعیت قابل تایید نیست")

    promise.status = PromiseStatus.DONE
    promise.resolved_at = datetime.now(timezone.utc)
    await apply_done_score(session, promise.giver_id, promise)
    await session.flush()
    if notifier:
        await notifier.on_confirm_done(promise, confirmer_name=str(actor_id))
    return ActionResult(ok=True, promise=promise)


async def dispute_done(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Receiver disputes a CLAIMED_DONE promise -> DISPUTED + immediate penalty."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.receiver_id != actor_id:
        return ActionResult(ok=False, error="فقط گیرنده قول می‌تونه رد کنه")
    if promise.status != PromiseStatus.CLAIMED_DONE:
        return ActionResult(ok=False, error="این قول در وضعیت قابل رد نیست")

    promise.status = PromiseStatus.DISPUTED
    await apply_disputed_score(session, promise.giver_id)
    await session.flush()
    if notifier:
        await notifier.on_disputed(promise, disputer_name=str(actor_id))
    return ActionResult(ok=True, promise=promise)


# ── Resolve dispute (receiver changes mind) ──────────────────────────────────

async def resolve_dispute(
    session: AsyncSession,
    promise_id: int,
    *,
    actor_id: int,
    notifier: PromiseNotifier | None = None,
) -> ActionResult:
    """Receiver resolves a DISPUTED promise -> DONE (penalty cancelled + done score)."""
    promise = await _load_promise(session, promise_id)
    if not promise:
        return ActionResult(ok=False, error="قول پیدا نشد!")
    if promise.receiver_id != actor_id:
        return ActionResult(ok=False, error="فقط گیرنده قول می‌تونه این کار رو بکنه")
    if promise.status != PromiseStatus.DISPUTED:
        return ActionResult(ok=False, error="این قول در وضعیت DISPUTED نیست")

    promise.status = PromiseStatus.DONE
    promise.resolved_at = datetime.now(timezone.utc)
    await resolve_dispute_to_done(session, promise.giver_id, promise)
    await session.flush()
    if notifier:
        await notifier.on_resolved(promise)
    return ActionResult(ok=True, promise=promise)


# ── Expiry (periodic job — implements the TODO in bot.py) ───────────────────

async def expire_overdue_promises(session: AsyncSession, now: datetime | None = None) -> list[Promise]:
    """Find promises past their deadline that are still open and mark EXPIRED.

    Open states: CONFIRMED, CLAIMED_DONE (PENDING is excluded — the receiver
    never accepted, so it isn't the giver's fault yet; matches bot semantics).
    Applies the expired penalty and returns the list for notification.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stmt = (
        select(Promise)
        .where(
            Promise.deadline.isnot(None),
            Promise.deadline < now,
            Promise.status.in_([PromiseStatus.CONFIRMED, PromiseStatus.CLAIMED_DONE]),
        )
    )
    res = await session.execute(stmt)
    promises = list(res.scalars().all())

    for p in promises:
        p.status = PromiseStatus.EXPIRED
        p.resolved_at = now
        await apply_expired_score(session, p.giver_id)
    if promises:
        await session.flush()
    return promises
