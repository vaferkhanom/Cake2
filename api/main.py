"""Promise Bot — Mini App API (FastAPI).

Companion backend for the Telegram Mini App. Validates Telegram initData,
exposes REST endpoints over the shared domain layer (src/domain), and can
optionally serve the built webapp as static files.

Run (dev):
    uvicorn api.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.auth import TelegramUser, get_telegram_user
from api.schemas import (
    MeOut,
    PromiseCreate,
    PromiseListOut,
    PromiseOut,
    RespondIn,
    UserOut,
)
from src.database import session as db
from src.database.models import Promise, PromiseStatus, TargetType, User
from src.database.session import (
    create_stub_user,
    get_or_create_user,
    get_session,
    get_user_by_id,
    get_user_by_username,
)
from src.domain import promise_actions as pa
from src.domain.promise_actions import NoopNotifier
from src.keyboards.inline import get_status_emoji, get_status_text
from src.utils.format import format_jalali_date, format_jalali_short

logger = logging.getLogger(__name__)

WEBAPP_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist (dev/SQLite; production uses Alembic migrations).
    if not db.settings.DATABASE_URL:
        await db.init_db()
    yield


app = FastAPI(title="Promise Bot Mini App API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Mini Apps have no stable origin; auth is via initData
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Serialization helpers ───────────────────────────────────────────────────

def _name_for(user: User | None) -> str:
    if user is None:
        return ""
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.telegram_id)


def serialize_promise(p: Promise, viewer_id: int) -> PromiseOut:
    return PromiseOut(
        id=p.id,
        promise_id=p.promise_id,
        content=p.content,
        giver_id=p.giver_id,
        receiver_id=p.receiver_id,
        target_type=p.target_type.value,
        status=p.status.value,
        deadline=p.deadline,
        created_at=p.created_at,
        claimed_done_at=p.claimed_done_at,
        resolved_at=p.resolved_at,
        status_text=get_status_text(p.status),
        status_emoji=get_status_emoji(p.status),
        jalali_created_at=format_jalali_date(p.created_at),
        jalali_deadline=format_jalali_short(p.deadline) if p.deadline else None,
        giver_name=_name_for(p.giver) if p.giver else "",
        receiver_name=_name_for(p.receiver) if p.receiver else "",
        is_giver=p.giver_id == viewer_id,
        is_receiver=p.receiver_id == viewer_id,
    )


# ── Auth / me ───────────────────────────────────────────────────────────────

@app.get("/api/me", response_model=MeOut)
async def me(user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        db_user = await get_or_create_user(
            s,
            telegram_id=user.id,
            username=user.username or None,
            full_name=(user.first_name + (" " + user.last_name if user.last_name else "")).strip(),
        )
        uid = user.id

        total_given = (await s.execute(
            select(func.count(Promise.id)).where(Promise.giver_id == uid)
        )).scalar() or 0
        done = (await s.execute(
            select(func.count(Promise.id)).where(
                Promise.giver_id == uid, Promise.status == PromiseStatus.DONE
            )
        )).scalar() or 0
        broken = (await s.execute(
            select(func.count(Promise.id)).where(
                Promise.giver_id == uid, Promise.status == PromiseStatus.BROKEN
            )
        )).scalar() or 0
        total_received = (await s.execute(
            select(func.count(Promise.id)).where(Promise.receiver_id == uid)
        )).scalar() or 0
        accepted = (await s.execute(
            select(func.count(Promise.id)).where(
                Promise.receiver_id == uid,
                Promise.status.in_([PromiseStatus.CONFIRMED, PromiseStatus.DONE]),
            )
        )).scalar() or 0

        user_out = UserOut(
            telegram_id=db_user.telegram_id,
            username=db_user.username,
            full_name=db_user.full_name,
            score=db_user.score,
            current_streak=db_user.current_streak,
            display_name=db_user.display_name,
            created_at=db_user.created_at,
        )

    return MeOut(
        user=user_out,
        stats={
            "total_given": total_given,
            "done": done,
            "broken": broken,
            "total_received": total_received,
            "accepted": accepted,
        },
    )


# ── Promises CRUD ───────────────────────────────────────────────────────────

PAGE_SIZE = 10


@app.get("/api/promises", response_model=PromiseListOut)
async def list_promises(
    type: str = Query("self", pattern="^(self|given|received)$"),
    page: int = Query(0, ge=0),
    user: TelegramUser = Depends(get_telegram_user),
):
    uid = user.id
    async with get_session() as s:
        if type == "self":
            cond = (Promise.giver_id == uid, Promise.target_type == TargetType.SELF)
        elif type == "given":
            cond = (Promise.giver_id == uid, Promise.target_type == TargetType.FRIEND)
        else:
            cond = (Promise.receiver_id == uid, Promise.target_type == TargetType.FRIEND)

        total = (await s.execute(select(func.count(Promise.id)).where(*cond))).scalar() or 0
        stmt = (
            select(Promise)
            .where(*cond)
            .order_by(Promise.created_at.desc())
            .offset(page * PAGE_SIZE)
            .limit(PAGE_SIZE)
            .options(selectinload(Promise.giver), selectinload(Promise.receiver))
        )
        rows = (await s.execute(stmt)).scalars().all()

    items = [serialize_promise(p, uid) for p in rows]
    return PromiseListOut(
        type=type,
        page=page,
        total=total,
        total_pages=(total + PAGE_SIZE - 1) // PAGE_SIZE,
        items=items,
    )


@app.get("/api/promises/{promise_id}", response_model=PromiseOut)
async def get_promise(promise_id: int, user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        stmt = (
            select(Promise)
            .where(Promise.id == promise_id)
            .options(selectinload(Promise.giver), selectinload(Promise.receiver))
        )
        p = (await s.execute(stmt)).scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="قول پیدا نشد")
        if p.giver_id != user.id and p.receiver_id != user.id:
            raise HTTPException(status_code=403, detail="شما به این قول دسترسی ندارید")
        return serialize_promise(p, user.id)


@app.post("/api/promises", response_model=PromiseOut, status_code=201)
async def create_promise_api(body: PromiseCreate, user: TelegramUser = Depends(get_telegram_user)):
    if body.target_type == "self":
        async with get_session() as s:
            res = await pa.create_promise(
                s,
                giver_id=user.id,
                content=body.content,
                target_type=TargetType.SELF,
                deadline=body.deadline,
                notifier=NoopNotifier(),
            )
            if not res.ok:
                raise HTTPException(status_code=400, detail=res.error)
            p = res.promise
            stmt = (
                select(Promise).where(Promise.id == p.id)
                .options(selectinload(Promise.giver), selectinload(Promise.receiver))
            )
            p = (await s.execute(stmt)).scalar_one()
            return serialize_promise(p, user.id)
    else:
        if not body.receiver_username:
            raise HTTPException(status_code=400, detail="receiver_username الزامی است")
        username = body.receiver_username.lstrip("@")
        async with get_session() as s:
            receiver = await get_user_by_username(s, username)
            if receiver:
                receiver_id = receiver.telegram_id
            else:
                stub = await create_stub_user(s, username)
                receiver_id = stub.telegram_id
            res = await pa.create_promise(
                s,
                giver_id=user.id,
                content=body.content,
                target_type=TargetType.FRIEND,
                receiver_id=receiver_id,
                deadline=body.deadline,
                notifier=NoopNotifier(),
            )
            if not res.ok:
                raise HTTPException(status_code=400, detail=res.error)
            p = res.promise
            stmt = (
                select(Promise).where(Promise.id == p.id)
                .options(selectinload(Promise.giver), selectinload(Promise.receiver))
            )
            p = (await s.execute(stmt)).scalar_one()
            return serialize_promise(p, user.id)


# ── Promise actions (shared domain layer) ───────────────────────────────────

def _run_action(res: pa.ActionResult, not_found_msg: str = "قول پیدا نشد"):
    if not res.ok:
        raise HTTPException(status_code=400, detail=res.error)
    return res


@app.post("/api/promises/{promise_id}/respond")
async def respond_promise(
    promise_id: int,
    body: RespondIn,
    user: TelegramUser = Depends(get_telegram_user),
):
    async with get_session() as s:
        if body.action == "accept":
            res = await pa.accept_promise(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        else:
            res = await pa.reject_promise(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        _run_action(res)
        if res.deleted:
            return {"ok": True, "deleted": True, "promise_id": promise_id}
        p = res.promise
        stmt = (
            select(Promise).where(Promise.id == p.id)
            .options(selectinload(Promise.giver), selectinload(Promise.receiver))
        )
        p = (await s.execute(stmt)).scalar_one()
        return {"ok": True, "promise": serialize_promise(p, user.id).model_dump()}


@app.post("/api/promises/{promise_id}/claim-done")
async def claim_done_api(promise_id: int, user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        res = await pa.claim_done(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        _run_action(res)
        return {"ok": True, "status": res.promise.status.value}


@app.post("/api/promises/{promise_id}/broken")
async def broken_api(promise_id: int, user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        res = await pa.mark_broken(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        _run_action(res)
        return {"ok": True, "status": res.promise.status.value}


@app.post("/api/promises/{promise_id}/confirm-done")
async def confirm_done_api(promise_id: int, user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        res = await pa.confirm_done(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        _run_action(res)
        return {"ok": True, "status": res.promise.status.value}


@app.post("/api/promises/{promise_id}/dispute")
async def dispute_api(promise_id: int, user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        res = await pa.dispute_done(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        _run_action(res)
        return {"ok": True, "status": res.promise.status.value}


@app.post("/api/promises/{promise_id}/resolve-dispute")
async def resolve_dispute_api(promise_id: int, user: TelegramUser = Depends(get_telegram_user)):
    async with get_session() as s:
        res = await pa.resolve_dispute(s, promise_id, actor_id=user.id, notifier=NoopNotifier())
        _run_action(res)
        return {"ok": True, "status": res.promise.status.value}


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Static webapp (built frontend) ──────────────────────────────────────────

if WEBAPP_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEBAPP_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the built SPA; fall back to index.html for client routes."""
        candidate = WEBAPP_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = WEBAPP_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="webapp not built")
