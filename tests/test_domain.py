"""Tests for the shared domain layer (src/domain/promise_actions.py).

Covers the full promise state machine, scoring side-effects, permission
enforcement, and the expiry job. Uses a plain in-memory SQLite database and the
real scoring functions — no mocks for business logic.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.database.models import Base, Promise, PromiseStatus, TargetType, User
from src.database.session import create_promise as create_promise_row, get_or_create_user
from src.domain import promise_actions as pa
from src.services.scoring import SCORE_DONE_BASE, SCORE_BROKEN_CONFESSION, SCORE_DISPUTED_PENALTY, SCORE_EXPIRED


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(
        "sqlite+aiosqlite://", echo=False,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await eng.dispose()


@asynccontextmanager
async def _session_cm(factory):
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _mk_user(factory, uid: int, username: str | None = None, name: str | None = None) -> None:
    async with factory() as s:
        await get_or_create_user(s, uid, username or f"u{uid}", name or f"User {uid}")
        await s.commit()


async def _mk_promise(factory, giver: int, content: str, target: TargetType,
                      receiver: int | None = None, status: PromiseStatus = PromiseStatus.CONFIRMED,
                      deadline: datetime | None = None) -> Promise:
    async with factory() as s:
        p = await create_promise_row(
            s, giver, content, target,
            receiver if receiver is not None else giver,
            status, deadline=deadline,
        )
        await s.commit()
        return p


async def _get_promise(factory, pid: int) -> Promise | None:
    async with factory() as s:
        return await s.get(Promise, pid)


async def _get_user(factory, uid: int) -> User | None:
    async with factory() as s:
        return await s.get(User, uid)


# ── Create ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_self_promise_confirmed_immediately(db):
    await _mk_user(db, 100)
    async with _session_cm(db) as s:
        res = await pa.create_promise(
            s, giver_id=100, content="ورزش کنم", target_type=TargetType.SELF,
        )
        assert res.ok
        assert res.promise.status == PromiseStatus.CONFIRMED
        assert res.promise.receiver_id == 100
        assert res.promise.target_type == TargetType.SELF


@pytest.mark.asyncio
async def test_create_friend_promise_pending(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    async with _session_cm(db) as s:
        res = await pa.create_promise(
            s, giver_id=100, content="قول دوستانه", target_type=TargetType.FRIEND,
            receiver_id=200,
        )
        assert res.ok
        assert res.promise.status == PromiseStatus.PENDING


@pytest.mark.asyncio
async def test_create_empty_content_rejected(db):
    await _mk_user(db, 100)
    async with _session_cm(db) as s:
        res = await pa.create_promise(
            s, giver_id=100, content="   ", target_type=TargetType.SELF,
        )
        assert not res.ok
        assert "خالی" in res.error


# ── Accept / reject ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_promise(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.PENDING)

    async with _session_cm(db) as s:
        res = await pa.accept_promise(s, p.id, actor_id=200)
        assert res.ok
        assert res.promise.status == PromiseStatus.CONFIRMED

    assert (await _get_promise(db, p.id)).status == PromiseStatus.CONFIRMED


@pytest.mark.asyncio
async def test_accept_by_wrong_user_denied(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.PENDING)

    async with _session_cm(db) as s:
        res = await pa.accept_promise(s, p.id, actor_id=999)
        assert not res.ok
        assert "برای شما نیست" in res.error

    assert (await _get_promise(db, p.id)).status == PromiseStatus.PENDING


@pytest.mark.asyncio
async def test_reject_deletes_promise(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.PENDING)

    async with _session_cm(db) as s:
        res = await pa.reject_promise(s, p.id, actor_id=200)
        assert res.ok
        assert res.deleted

    assert (await _get_promise(db, p.id)) is None


# ── Claim / broken (giver) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_claim_done_giver_only(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.CONFIRMED)

    # receiver cannot claim
    async with _session_cm(db) as s:
        res = await pa.claim_done(s, p.id, actor_id=200)
        assert not res.ok
        assert "قول‌دهنده" in res.error

    # giver can
    async with _session_cm(db) as s:
        res = await pa.claim_done(s, p.id, actor_id=100)
        assert res.ok
        assert res.promise.status == PromiseStatus.CLAIMED_DONE
        assert res.promise.claimed_done_at is not None


@pytest.mark.asyncio
async def test_claim_done_only_from_confirmed(db):
    await _mk_user(db, 100)
    p = await _mk_promise(db, 100, "t", TargetType.SELF, 100, PromiseStatus.PENDING)

    async with _session_cm(db) as s:
        res = await pa.claim_done(s, p.id, actor_id=100)
        assert not res.ok
        assert "تایید شده" in res.error


@pytest.mark.asyncio
async def test_mark_broken_applies_penalty(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.CONFIRMED)

    async with _session_cm(db) as s:
        res = await pa.mark_broken(s, p.id, actor_id=100)
        assert res.ok
        assert res.promise.status == PromiseStatus.BROKEN

    assert (await _get_user(db, 100)).score == SCORE_BROKEN_CONFESSION
    assert (await _get_user(db, 100)).current_streak == 0


@pytest.mark.asyncio
async def test_mark_broken_self_no_penalty(db):
    await _mk_user(db, 100)
    p = await _mk_promise(db, 100, "t", TargetType.SELF, 100, PromiseStatus.CONFIRMED)

    async with _session_cm(db) as s:
        res = await pa.mark_broken(s, p.id, actor_id=100)
        assert res.ok

    assert (await _get_user(db, 100)).score == 0


# ── Confirm / dispute (receiver) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_done_scores_giver(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.CLAIMED_DONE)

    async with _session_cm(db) as s:
        res = await pa.confirm_done(s, p.id, actor_id=200)
        assert res.ok
        assert res.promise.status == PromiseStatus.DONE

    user = await _get_user(db, 100)
    assert user.score == SCORE_DONE_BASE
    assert user.current_streak == 1


@pytest.mark.asyncio
async def test_confirm_done_self_no_score(db):
    await _mk_user(db, 100)
    p = await _mk_promise(db, 100, "t", TargetType.SELF, 100, PromiseStatus.CLAIMED_DONE)

    async with _session_cm(db) as s:
        res = await pa.confirm_done(s, p.id, actor_id=100)
        assert res.ok

    assert (await _get_user(db, 100)).score == 0


@pytest.mark.asyncio
async def test_dispute_applies_penalty(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.CLAIMED_DONE)

    async with _session_cm(db) as s:
        res = await pa.dispute_done(s, p.id, actor_id=200)
        assert res.ok
        assert res.promise.status == PromiseStatus.DISPUTED

    assert (await _get_user(db, 100)).score == SCORE_DISPUTED_PENALTY


@pytest.mark.asyncio
async def test_resolve_dispute_scores_full_done(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    p = await _mk_promise(db, 100, "t", TargetType.FRIEND, 200, PromiseStatus.DISPUTED)

    async with _session_cm(db) as s:
        res = await pa.resolve_dispute(s, p.id, actor_id=200)
        assert res.ok
        assert res.promise.status == PromiseStatus.DONE

    # -5 (penalty cancelled) + 10 (base) + 10 (first-streak bonus, capped) = 15
    user = await _get_user(db, 100)
    assert user.score == SCORE_DISPUTED_PENALTY + SCORE_DONE_BASE + 10


# ── Expiry job ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expire_overdue_promises(db):
    await _mk_user(db, 100)
    await _mk_user(db, 200)
    now = datetime.now(timezone.utc)

    overdue_confirmed = await _mk_promise(
        db, 100, "overdue confirmed", TargetType.FRIEND, 200,
        PromiseStatus.CONFIRMED, deadline=now - timedelta(days=1),
    )
    overdue_claimed = await _mk_promise(
        db, 100, "overdue claimed", TargetType.FRIEND, 200,
        PromiseStatus.CLAIMED_DONE, deadline=now - timedelta(hours=2),
    )
    not_overdue = await _mk_promise(
        db, 100, "future", TargetType.FRIEND, 200,
        PromiseStatus.CONFIRMED, deadline=now + timedelta(days=3),
    )
    pending_overdue = await _mk_promise(
        db, 100, "pending overdue", TargetType.FRIEND, 200,
        PromiseStatus.PENDING, deadline=now - timedelta(days=5),
    )

    async with _session_cm(db) as s:
        expired = await pa.expire_overdue_promises(s, now=now)

    ids = {p.id for p in expired}
    assert overdue_confirmed.id in ids
    assert overdue_claimed.id in ids
    assert not_overdue.id not in ids
    assert pending_overdue.id not in ids  # PENDING is not the giver's fault

    assert (await _get_promise(db, overdue_confirmed.id)).status == PromiseStatus.EXPIRED
    assert (await _get_promise(db, overdue_claimed.id)).status == PromiseStatus.EXPIRED
    assert (await _get_promise(db, not_overdue.id)).status == PromiseStatus.CONFIRMED
    assert (await _get_promise(db, pending_overdue.id)).status == PromiseStatus.PENDING
    assert (await _get_user(db, 100)).score == 2 * SCORE_EXPIRED
    assert (await _get_user(db, 100)).current_streak == 0
