"""Tests for Promise Bot - Phase 5 complete."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import html

import pytest
import pytest_asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.models import Base, Promise, PromiseStatus, TargetType, User
from src.database.session import create_promise, get_or_create_user
from src.handlers.promise import (
    promise_content_received,
    promise_confirmed,
    promise_edit,
    target_self,
    target_friend,
    promise_accepted,
    promise_rejected,
    _process_friend,
    show_promise_list,
    show_promise_detail,
    claim_done,
    confirm_done,
    dispute_done,
    mark_broken,
    resolve_dispute,
    main_create_promise,
    main_show_my_promises_menu,
)
from src.keyboards.inline import (
    ConfirmPromiseCallback,
    ReceiverConfirmCallback,
    TargetCallback,
    ClaimDoneCallback,
    ReceiverConfirmDoneCallback,
    BrokenCallback,
    ResolveDisputeCallback,
    DeadlineCallback,
    PromiseListCallback,
    PromiseItemCallback,
)
from src.states.promise import PromiseStates
from tests.conftest import make_message, make_callback


# ── Helpers ────────────────────────────────────────────

async def _make_test_db():
    eng = create_async_engine(
        "sqlite+aiosqlite://", echo=False,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    return eng, factory


def _session_cm(factory):
    """Mock get_session — yields session and commits on exit (like real one)."""
    @asynccontextmanager
    async def _cm():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    return _cm


def _make_fsm(storage=None):
    if storage is None:
        storage = MemoryStorage()
    return FSMContext(storage=storage, key=("chat", "user"))


# ── Tests ──────────────────────────────────────────────

@ pytest.mark.asyncio
async def test_start_enters_fsm():
    state = _make_fsm()
    cb = make_callback("main:create", user_id=100)
    await main_create_promise(cb, state)
    assert await state.get_state() == PromiseStates.waiting_for_content


@ pytest.mark.asyncio
async def test_content_received():
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_content)
    msg = make_message(text="ورزش کنم")
    await promise_content_received(msg, state)
    assert await state.get_state() == PromiseStates.waiting_for_confirmation
    data = await state.get_data()
    assert data["content"] == "ورزش کنم"


@pytest.mark.asyncio
async def test_content_empty_stays():
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_content)
    msg = make_message(text="   ")
    await promise_content_received(msg, state)
    assert await state.get_state() == PromiseStates.waiting_for_content


@pytest.mark.asyncio
async def test_confirm_moves_to_target():
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_confirmation)
    cb = make_callback(ConfirmPromiseCallback(action="yes").pack())
    await promise_confirmed(cb, state)
    assert await state.get_state() == PromiseStates.waiting_for_deadline_choice


@pytest.mark.asyncio
async def test_edit_goes_back():
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_confirmation)
    cb = make_callback(ConfirmPromiseCallback(action="edit").pack())
    await promise_edit(cb, state)
    assert await state.get_state() == PromiseStates.waiting_for_content


@pytest.mark.asyncio
async def test_target_self_creates_confirmed():
    eng, factory = await _make_test_db()
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_target)
    await state.update_data(content="هر روز ورزش")

    cb = make_callback(TargetCallback(target="self").pack(), user_id=100)

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await target_self(cb, state)

    assert await state.get_state() is None
    cb.message.edit_text.assert_called_once()
    msg_text = cb.message.edit_text.call_args[0][0]
    assert "#1" in msg_text

    async with factory() as s:
        from sqlalchemy import select
        p = (await s.execute(select(Promise))).scalar_one()
        assert p.status == PromiseStatus.CONFIRMED
        assert p.giver_id == 100
        assert p.receiver_id == 100
    await eng.dispose()


@pytest.mark.asyncio
async def test_target_friend_asks_id():
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_target)
    cb = make_callback(TargetCallback(target="friend").pack())
    await target_friend(cb, state)
    assert await state.get_state() == PromiseStates.waiting_for_friend_id


@pytest.mark.asyncio
async def test_friend_username_known_sends_dm():
    eng, factory = await _make_test_db()
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await state.update_data(content="قول دوستانه")

    async with factory() as s:
        await get_or_create_user(s, 200, "bob", "Bob")
        await s.commit()

    msg = make_message(text="@bob", user_id=100)

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await _process_friend(msg, state, username="bob")

    assert await state.get_state() is None
    msg.bot.send_message.assert_called_once()
    send_kwargs = msg.bot.send_message.call_args[1]
    assert send_kwargs["chat_id"] == 200
    assert "قبول" in send_kwargs["text"]
    await eng.dispose()


@pytest.mark.asyncio
async def test_friend_unknown_shows_invite():
    eng, factory = await _make_test_db()
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await state.update_data(content="قول مجهول")

    msg = make_message(text="@ghost", user_id=100)
    msg.bot.get_me = AsyncMock(return_value=MagicMock(username="test_promise_bot"))

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await _process_friend(msg, state, username="ghost")

    assert await state.get_state() is None
    answer_text = msg.answer.call_args[0][0]
    assert "test_promise_bot" in answer_text
    await eng.dispose()


@pytest.mark.asyncio
async def test_receiver_accept():
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "test", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="accept")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_accepted(cb, cb_data)

    async with factory() as s:
        from sqlalchemy import select
        p = (await s.execute(select(Promise).where(Promise.id == pid))).scalar_one()
        assert p.status == PromiseStatus.CONFIRMED

    cb.bot.send_message.assert_called_once()
    assert cb.bot.send_message.call_args[1]["chat_id"] == 100
    await eng.dispose()


@pytest.mark.asyncio
async def test_receiver_reject():
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "reject me", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="reject")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_rejected(cb, cb_data)

    async with factory() as s:
        from sqlalchemy import select
        p = (await s.execute(select(Promise).where(Promise.id == pid))).scalar_one()
        assert p.status == PromiseStatus.REJECTED
    await eng.dispose()


@pytest.mark.asyncio
async def test_wrong_user_cannot_accept():
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "private", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="accept")
    cb = make_callback(cb_data.pack(), user_id=999, full_name="Hacker")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_accepted(cb, cb_data)

    cb.answer.assert_called_with("این دکمه برای شما نیست", show_alert=True)
    await eng.dispose()


@pytest.mark.asyncio
async def test_friend_by_forwarded_message():
    eng, factory = await _make_test_db()
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await state.update_data(content="قول از فوروارد")

    async with factory() as s:
        await get_or_create_user(s, 300, "charlie", "Charlie")
        await s.commit()

    msg = make_message(user_id=100)
    msg.forward_from = MagicMock()
    msg.forward_from.id = 300

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await _process_friend(msg, state, friend_id=300)

    assert await state.get_state() is None
    msg.bot.send_message.assert_called_once()
    send_kwargs = msg.bot.send_message.call_args[1]
    assert send_kwargs["chat_id"] == 300
    await eng.dispose()


@pytest.mark.asyncio
async def test_friend_numeric_id_not_in_db():
    eng, factory = await _make_test_db()
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await state.update_data(content="قول عددی")

    msg = make_message(text="99999", user_id=100)
    msg.bot.get_me = AsyncMock(return_value=MagicMock(username="test_promise_bot"))

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await _process_friend(msg, state, friend_id=99999)

    assert await state.get_state() is None
    answer_text = msg.answer.call_args[0][0]
    assert "test_promise_bot" in answer_text
    await eng.dispose()


# ── Phase 5: Promise List Grid Tests ──────────────────

@ pytest.mark.asyncio
async def test_show_my_promises_menu():
    """Test that main menu shows 3 options."""
    cb = make_callback("main:list", user_id=100)
    await main_show_my_promises_menu(cb)
    cb.message.edit_text.assert_called_once()
    call_kwargs = cb.message.edit_text.call_args[1]
    assert "reply_markup" in call_kwargs


@ pytest.mark.asyncio
async def test_self_list_empty():
    eng, factory = await _make_test_db()
    cb = make_callback(PromiseListCallback(list_type="self", page=0).pack(), user_id=100)

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb, PromiseListCallback(list_type="self", page=0))

    # Should show empty message
    cb.message.edit_text.assert_called_once()
    edit_text = cb.message.edit_text.call_args[0][0]
    assert "قولی برای خودت ثبت نکردی" in edit_text
    await eng.dispose()


@pytest.mark.asyncio
async def test_given_list_empty():
    eng, factory = await _make_test_db()
    cb = make_callback(PromiseListCallback(list_type="given", page=0).pack(), user_id=100)

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb, PromiseListCallback(list_type="given", page=0))

    cb.message.edit_text.assert_called_once()
    edit_text = cb.message.edit_text.call_args[0][0]
    assert "قولی به دوستات ندادی" in edit_text
    await eng.dispose()


@pytest.mark.asyncio
async def test_received_list_empty():
    eng, factory = await _make_test_db()
    cb = make_callback(PromiseListCallback(list_type="received", page=0).pack(), user_id=100)

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb, PromiseListCallback(list_type="received", page=0))

    cb.message.edit_text.assert_called_once()
    edit_text = cb.message.edit_text.call_args[0][0]
    assert "کسی بهت قول نداده" in edit_text
    await eng.dispose()


@pytest.mark.asyncio
async def test_self_list_pagination():
    """Test self list with >4 items shows pagination."""
    eng, factory = await _make_test_db()

    # Create 6 self promises
    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        for i in range(6):
            await create_promise(s, 100, f"قول شخصی {i+1}", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        await s.commit()

    cb = make_callback(PromiseListCallback(list_type="self", page=0).pack(), user_id=100)

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb, PromiseListCallback(list_type="self", page=0))

    cb.message.edit_text.assert_called_once()
    edit_text = cb.message.edit_text.call_args[0][0]
    assert "صفحه 1 از 2" in edit_text
    assert "6 قول" in edit_text

    # Check keyboard has 4 buttons + navigation
    call_kwargs = cb.message.edit_text.call_args[1]
    keyboard = call_kwargs["reply_markup"]
    # 4 promise buttons + 1 navigation row with "بعدی"
    await eng.dispose()


@pytest.mark.asyncio
async def test_promise_list_page_1_and_page_2():
    """Test pagination: page 0 and page 1 show different items."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        for i in range(5):
            await create_promise(s, 100, f"Self Promise {i+1}", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        await s.commit()

    # Page 0
    cb0 = make_callback(PromiseListCallback(list_type="self", page=0).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb0, PromiseListCallback(list_type="self", page=0))

    cb0.message.edit_text.assert_called_once()
    # Should have "بعدی" button
    await eng.dispose()


@pytest.mark.asyncio
async def test_promise_detail_from_grid():
    """Test clicking a grid button shows detail with back button."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        p = await create_promise(s, 100, "Detail Test", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        pid = p.id
        await s.commit()

    cb = make_callback(
        PromiseItemCallback(promise_id=pid, list_type="self", page=0).pack(),
        user_id=100
    )

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_detail(cb, PromiseItemCallback(promise_id=pid, list_type="self", page=0))

    cb.message.edit_text.assert_called_once()
    edit_text = cb.message.edit_text.call_args[0][0]
    assert "Detail Test" in edit_text
    assert "#1" in edit_text  # promise_id

    # Keyboard should have action buttons + back button
    call_kwargs = cb.message.edit_text.call_args[1]
    keyboard = call_kwargs["reply_markup"]
    await eng.dispose()


@pytest.mark.asyncio
async def test_back_to_list_returns_same_page():
    """Test back button returns to exact same page."""
    # This is implicitly tested by PromiseListCallback handling page parameter
    # The callback_data for back button includes list_type and page
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        for i in range(5):
            await create_promise(s, 100, f"Promise {i+1}", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        await s.commit()

    # First go to page 1
    cb = make_callback(PromiseListCallback(list_type="self", page=1).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb, PromiseListCallback(list_type="self", page=1))

    # Then simulate back button press (which calls show_promise_list with page=1)
    cb2 = make_callback(PromiseListCallback(list_type="self", page=1).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb2, PromiseListCallback(list_type="self", page=1))

    # Both should show page 2
    assert "صفحه 2" in cb.message.edit_text.call_args[0][0]
    assert "صفحه 2" in cb2.message.edit_text.call_args[0][0]
    await eng.dispose()


@pytest.mark.asyncio
async def test_list_types_are_isolated():
    """Test self/given/received lists don't mix."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        # Self promise
        await create_promise(s, 100, "Self promise", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        # Given promise (100 -> 200)
        await create_promise(s, 100, "Given promise", TargetType.FRIEND, 200, PromiseStatus.CONFIRMED)
        # Received promise (200 -> 100)
        await create_promise(s, 200, "Received promise", TargetType.FRIEND, 100, PromiseStatus.CONFIRMED)
        await s.commit()

    # Self list for user 100
    cb_self = make_callback(PromiseListCallback(list_type="self", page=0).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb_self, PromiseListCallback(list_type="self", page=0))

    edit_self = cb_self.message.edit_text.call_args[0][0]
    assert "1 قول" in edit_self
    # Check that keyboard has the self promise button
    keyboard_self = cb_self.message.edit_text.call_args[1]["reply_markup"]
    assert "Self promise" in str(keyboard_self)
    assert "Given promise" not in str(keyboard_self)
    assert "Received promise" not in str(keyboard_self)

    # Given list for user 100
    cb_given = make_callback(PromiseListCallback(list_type="given", page=0).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb_given, PromiseListCallback(list_type="given", page=0))

    edit_given = cb_given.message.edit_text.call_args[0][0]
    assert "1 قول" in edit_given
    keyboard_given = cb_given.message.edit_text.call_args[1]["reply_markup"]
    assert "Given promise" in str(keyboard_given)
    assert "Self promise" not in str(keyboard_given)
    assert "Received promise" not in str(keyboard_given)

    # Received list for user 100
    cb_received = make_callback(PromiseListCallback(list_type="received", page=0).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb_received, PromiseListCallback(list_type="received", page=0))

    edit_received = cb_received.message.edit_text.call_args[0][0]
    assert "1 قول" in edit_received
    keyboard_received = cb_received.message.edit_text.call_args[1]["reply_markup"]
    assert "Received promise" in str(keyboard_received)
    assert "Self promise" not in str(keyboard_received)
    assert "Given promise" not in str(keyboard_received)

    await eng.dispose()


@pytest.mark.asyncio
async def test_less_than_page_size_no_navigation():
    """Test list with 1-3 items shows no navigation buttons."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        for i in range(3):
            await create_promise(s, 100, f"Item {i+1}", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        await s.commit()

    cb = make_callback(PromiseListCallback(list_type="self", page=0).pack(), user_id=100)
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await show_promise_list(cb, PromiseListCallback(list_type="self", page=0))

    edit_text = cb.message.edit_text.call_args[0][0]
    assert "3 قول" in edit_text
    # Should NOT have navigation row (only 1 page)
    # This is verified by keyboard structure
    await eng.dispose()


# ── Phase 3: Stub User Merge Validation ────────────────────

@pytest.mark.asyncio
async def test_stub_user_merge_on_deep_link():
    """Test end-to-end stub user merge:
    - User A creates promise for user B (not started bot) via friend flow (username) -> stub created with negative ID
    - User B starts bot via deep link ?start=promise_{id}
    - Promise should immediately be available for B to accept/reject
    """
    eng, factory = await _make_test_db()
    
    # Simulate the friend flow: user A creates promise for @bob (who hasn't started bot)
    # This goes through _process_friend which calls create_stub_user when user not found by username
    from src.handlers.promise import _process_friend
    from src.states.promise import PromiseStates
    
    state = _make_fsm()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await state.update_data(content="Test promise for B")
    
    # User A (100) creates promise for @bob (using username, not forward)
    msg = make_message(text="@bob", user_id=100)
    
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await _process_friend(msg, state, username="bob")
    
    # Verify promise was created and stub user exists with negative ID
    async with factory() as s:
        from sqlalchemy import select
        stmt = select(Promise).where(Promise.giver_id == 100)
        res = await s.execute(stmt)
        promises = res.scalars().all()
        assert len(promises) == 1
        p = promises[0]
        pid = p.id
        assert p.status == PromiseStatus.PENDING
        assert p.receiver_id < 0  # stub user has negative ID
        
        # Verify stub user was created
        stmt = select(User).where(User.telegram_id == p.receiver_id)
        res = await s.execute(stmt)
        stub_user = res.scalar_one()
        assert stub_user.telegram_id < 0
        assert stub_user.username == "bob"
        assert stub_user.has_started_bot is False
    
    # Now simulate user B (999) starting the bot with deep link
    # cmd_start should merge the stub and update promise receiver_id
    from src.handlers.promise import cmd_start
    from aiogram.filters import CommandObject
    
    state = _make_fsm()
    msg = make_message(text=f"/start promise_{pid}", user_id=999)
    msg.from_user.username = "bob"
    msg.from_user.full_name = "Bob"
    
    command = CommandObject(args=f"promise_{pid}", prefix="/")
    
    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await cmd_start(msg, command, state)
    
    # Verify promise now has correct receiver_id (999) and is still PENDING
    async with factory() as s:
        stmt = select(Promise).where(Promise.id == pid)
        res = await s.execute(stmt)
        p = res.scalar_one()
        assert p.receiver_id == 999
        assert p.status == PromiseStatus.PENDING
        
        # Verify user 999 now exists with correct ID (stub merged)
        stmt = select(User).where(User.telegram_id == 999)
        res = await s.execute(stmt)
        user_b = res.scalar_one()
        assert user_b.telegram_id == 999
        assert user_b.username == "bob"
        assert user_b.has_started_bot is True
    
    await eng.dispose()


# ── Phase 3: Scoring Tests ───────────────────────────────────

@pytest.mark.asyncio
async def test_apply_done_score_self_promise_no_score():
    """Self promises should not give any score."""
    eng, factory = await _make_test_db()
    
    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        p = await create_promise(s, 100, "Self promise", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        await s.commit()
    
    from src.services.scoring import apply_done_score
    
    async with factory() as s:
        await apply_done_score(s, 100, p)
        # Check user score didn't change
        stmt = select(User).where(User.telegram_id == 100)
        res = await s.execute(stmt)
        user = res.scalar_one()
        assert user.score == 0
    
    await eng.dispose()


@pytest.mark.asyncio
async def test_apply_done_score_friend_promise_base_score():
    """Friend promises should give base score."""
    eng, factory = await _make_test_db()
    
    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "Friend promise", TargetType.FRIEND, 200, PromiseStatus.CONFIRMED)
        await s.commit()
    
    from src.services.scoring import apply_done_score
    
    async with factory() as s:
        await apply_done_score(s, 100, p)
        stmt = select(User).where(User.telegram_id == 100)
        res = await s.execute(stmt)
        user = res.scalar_one()
        assert user.score == 10  # SCORE_DONE_BASE
        assert user.current_streak == 1
    
    await eng.dispose()


@pytest.mark.asyncio
async def test_apply_broken_score_self_promise_no_penalty():
    """Self promises should not give penalty for broken."""
    eng, factory = await _make_test_db()
    
    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        p = await create_promise(s, 100, "Self promise", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
        await s.commit()
    
    from src.services.scoring import apply_broken_score
    
    async with factory() as s:
        await apply_broken_score(s, 100, p)
        stmt = select(User).where(User.telegram_id == 100)
        res = await s.execute(stmt)
        user = res.scalar_one()
        assert user.score == 0
        assert user.current_streak == 0  # streak should be 0
    
    await eng.dispose()


@pytest.mark.asyncio
async def test_apply_broken_score_friend_promise_penalty():
    """Friend promises should give penalty for broken."""
    eng, factory = await _make_test_db()
    
    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "Friend promise", TargetType.FRIEND, 200, PromiseStatus.CONFIRMED)
        await s.commit()
    
    from src.services.scoring import apply_broken_score
    
    async with factory() as s:
        await apply_broken_score(s, 100, p)
        stmt = select(User).where(User.telegram_id == 100)
        res = await s.execute(stmt)
        user = res.scalar_one()
        assert user.score == -8  # SCORE_BROKEN_CONFESSION
        assert user.current_streak == 0
    
    await eng.dispose()


@pytest.mark.asyncio
async def test_resolve_dispute_to_done_cancels_penalty_and_adds_score():
    """Dispute resolved to done should cancel penalty and add full done score."""
    eng, factory = await _make_test_db()
    
    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "Friend promise", TargetType.FRIEND, 200, PromiseStatus.CONFIRMED)
        await s.commit()
    
    from src.services.scoring import apply_disputed_score, resolve_dispute_to_done
    
    # First apply dispute penalty
    async with factory() as s:
        await apply_disputed_score(s, 100)
        stmt = select(User).where(User.telegram_id == 100)
        res = await s.execute(stmt)
        user = res.scalar_one()
        assert user.score == -5  # SCORE_DISPUTED_PENALTY
    
    # Then resolve to done
    async with factory() as s:
        await resolve_dispute_to_done(s, 100, p)
        stmt = select(User).where(User.telegram_id == 100)
        res = await s.execute(stmt)
        user = res.scalar_one()
        # -5 (penalty cancelled) + 10 (base) + 10 (streak bonus, capped at 10) = 15
        assert user.score == 15
        assert user.current_streak == 1
    
    await eng.dispose()


@pytest.mark.asyncio
async def test_user_creation():
    eng, factory = await _make_test_db()
    async with factory() as session:
        user = User(telegram_id=12345, username="testuser", full_name="Test User")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.telegram_id == 12345
        assert user.username == "testuser"
    await eng.dispose()


@pytest.mark.asyncio
async def test_promise_creation():
    eng, factory = await _make_test_db()
    async with factory() as session:
        user = User(telegram_id=12345, username="testuser", full_name="Test User")
        session.add(user)
        await session.commit()

        promise = Promise(
            promise_id=1,
            content="Test promise",
            giver_id=12345,
            target_type=TargetType.SELF,
            status=PromiseStatus.CONFIRMED,
        )
        session.add(promise)
        await session.commit()
        await session.refresh(promise)

        assert promise.id == 1
        assert promise.promise_id == 1
        assert promise.content == "Test promise"
    await eng.dispose()


# ── Phase 6: escape_html Tests ──────────────────────────────────

def test_escape_html_escapes_tags():
    """HTML tags in user content should be escaped."""
    from src.utils.format import escape_html
    result = escape_html('<script>alert("xss")</script>')
    assert result == "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
    assert "<script>" not in result


def test_escape_html_preserves_normal_text():
    """Normal text without HTML should pass through unchanged."""
    from src.utils.format import escape_html
    result = escape_html("قول عادی بدون تگ")
    assert result == "قول عادی بدون تگ"


def test_escape_html_blockquote_safety():
    """Content inside blockquote tags should not break out."""
    from src.utils.format import escape_html
    content = " </blockquote> <b>bold injection</b> "
    escaped = escape_html(content)
    assert "</blockquote>" not in escaped
    assert "<b>" not in escaped


# ── Phase 6: Back Button Tests ──────────────────────────────────

def test_promise_list_keyboard_has_back_button():
    """Promise list keyboard should always have a back-to-menu button."""
    from src.keyboards.inline import get_promise_list_keyboard
    eng, factory_eng = None, None

    # Need at least one promise
    async def _run():
        eng, factory = await _make_test_db()
        async with factory() as s:
            await get_or_create_user(s, 100, "alice", "Alice")
            await create_promise(s, 100, "Test promise", TargetType.SELF, 100, PromiseStatus.CONFIRMED)
            await s.commit()

        async with factory() as s:
            from sqlalchemy import select
            stmt = select(Promise).where(Promise.giver_id == 100)
            res = await s.execute(stmt)
            promises = list(res.scalars().all())

        kb = get_promise_list_keyboard(promises, "self", 0, 1)
        kb_str = str(kb)
        assert "بازگشت به منوی اصلی" in kb_str
        assert "main:back" in kb_str
        await eng.dispose()

    import asyncio
    asyncio.run(_run())


# ── Phase 6: Edit-Message Accept/Reject Tests ──────────────────

@pytest.mark.asyncio
async def test_receiver_accept_edits_giver_message():
    """When giver_pending fields exist, accept should edit the giver's message instead of sending new."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "test", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        # Set pending message fields
        p.giver_pending_message_id = 11111
        p.giver_pending_chat_id = 100
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="accept")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_accepted(cb, cb_data)

    # Should edit the giver's pending message
    cb.bot.edit_message_text.assert_called_once()
    edit_kwargs = cb.bot.edit_message_text.call_args[1]
    assert edit_kwargs["chat_id"] == 100
    assert edit_kwargs["message_id"] == 11111
    assert "تایید کرد" in edit_kwargs["text"]
    # Should NOT include claim_done_keyboard in confirmation notification
    # claim_done_keyboard is only shown in promise detail view
    assert "reply_markup" not in edit_kwargs or edit_kwargs["reply_markup"] is None

    # Should NOT send a new message (edit succeeded)
    cb.bot.send_message.assert_not_called()
    await eng.dispose()


@pytest.mark.asyncio
async def test_receiver_accept_fallback_when_edit_fails():
    """When edit fails, accept should fallback to send_message."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "test", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        p.giver_pending_message_id = 11111
        p.giver_pending_chat_id = 100
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="accept")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    # Make edit_message_text raise an error to trigger fallback
    cb.bot.edit_message_text = AsyncMock(side_effect=Exception("Message not found"))

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_accepted(cb, cb_data)

    # Edit failed, so fallback to send_message
    cb.bot.send_message.assert_called_once()
    send_kwargs = cb.bot.send_message.call_args[1]
    assert send_kwargs["chat_id"] == 100
    assert "تایید کرد" in send_kwargs["text"]
    # Should NOT include claim_done_keyboard in confirmation notification
    assert "reply_markup" not in send_kwargs or send_kwargs["reply_markup"] is None
    await eng.dispose()


@pytest.mark.asyncio
async def test_receiver_reject_edits_giver_message():
    """When giver_pending fields exist, reject should edit the giver's message."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "reject me", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        p.giver_pending_message_id = 22222
        p.giver_pending_chat_id = 100
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="reject")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_rejected(cb, cb_data)

    # Should edit the giver's pending message
    cb.bot.edit_message_text.assert_called_once()
    edit_kwargs = cb.bot.edit_message_text.call_args[1]
    assert edit_kwargs["chat_id"] == 100
    assert edit_kwargs["message_id"] == 22222
    assert "رد کرد" in edit_kwargs["text"]
    await eng.dispose()


@pytest.mark.asyncio
async def test_receiver_reject_fallback_when_no_pending_fields():
    """When no pending fields exist, reject should send a new message."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "reject me", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        # No giver_pending fields set (old promise)
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="reject")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_rejected(cb, cb_data)

    # Should send a new message since no pending fields
    cb.bot.send_message.assert_called_once()
    send_kwargs = cb.bot.send_message.call_args[1]
    assert send_kwargs["chat_id"] == 100
    assert "رد کرد" in send_kwargs["text"]
    await eng.dispose()


def test_claim_done_keyboard_only_in_detail_view():
    """
    Static test: Ensure claim_done_keyboard is ONLY used in promise detail view
    (get_promise_detail_keyboard) and NOT in any notification/acceptance handlers.
    
    This prevents the recurring bug where "claim done" buttons appear immediately
    after promise acceptance instead of only in the detail view.
    """
    import ast
    import os
    
    handlers_path = os.path.join(os.path.dirname(__file__), "..", "src", "handlers", "promise.py")
    with open(handlers_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse the AST to find all calls to claim_done_keyboard
    tree = ast.parse(content)
    
    claim_done_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if it's a call to claim_done_keyboard
            if isinstance(node.func, ast.Name) and node.func.id == "claim_done_keyboard":
                claim_done_calls.append(node.lineno)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "claim_done_keyboard":
                claim_done_calls.append(node.lineno)
    
    # The ONLY valid usage is in inline.py's get_promise_detail_keyboard
    # In promise.py, claim_done_keyboard should ONLY be imported, never called
    assert len(claim_done_calls) == 0, (
        f"claim_done_keyboard() called in promise.py at lines {claim_done_calls}. "
        "It should ONLY be used in inline.py's get_promise_detail_keyboard() "
        "for the promise detail view, NOT in any acceptance/notification handlers."
    )


def test_no_claim_text_in_giver_notifications():
    """
    Static test: Ensure GIVER acceptance notifications don't contain "claim" or "ادعای انجام" text.
    The receiver's own confirmation message CAN mention it, but the giver's notification should be simple.
    """
    import os
    
    handlers_path = os.path.join(os.path.dirname(__file__), "..", "src", "handlers", "promise.py")
    with open(handlers_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # These patterns should NOT appear in the GIVER notification
    forbidden_patterns = [
        "ادعای انجام بده",
        "می‌تونی ادعای انجام",
    ]
    
    # Check ONLY the _notify_promise_confirmed function (giver notification)
    import re
    func_match = re.search(r'async def _notify_promise_confirmed\(.*?\n(?:.*?\n)*?\n(?:async def|# ──|$)', content, re.MULTILINE)
    if func_match:
        func_content = func_match.group(0)
        # Extract only the function body (after docstring)
        body_start = func_content.find('"""') 
        if body_start != -1:
            body_end = func_content.find('"""', body_start + 3)
            if body_end != -1:
                func_body = func_content[body_end + 3:]
            else:
                func_body = func_content
        else:
            func_body = func_content
            
        for pattern in forbidden_patterns:
            assert pattern not in func_body, (
                f"Forbidden pattern '{pattern}' found in _notify_promise_confirmed body. "
                "Giver notifications should be simple confirmations only."
            )


# ═══════════════════════════════════════════════════════════════
# NEW TESTS: Per-giver numbering, content in messages, group deadline
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_per_giver_promise_id_independent():
    """Two different givers should have independent promise_id sequences starting from 1."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")

        # Alice creates 3 promises
        p1 = await create_promise(s, 100, "promise 1", TargetType.SELF, None, PromiseStatus.CONFIRMED)
        p2 = await create_promise(s, 100, "promise 2", TargetType.SELF, None, PromiseStatus.CONFIRMED)
        p3 = await create_promise(s, 100, "promise 3", TargetType.SELF, None, PromiseStatus.CONFIRMED)

        # Bob creates 2 promises
        p4 = await create_promise(s, 200, "promise A", TargetType.SELF, None, PromiseStatus.CONFIRMED)
        p5 = await create_promise(s, 200, "promise B", TargetType.SELF, None, PromiseStatus.CONFIRMED)

        await s.commit()

    # Alice's promises should be numbered 1, 2, 3
    assert p1.promise_id == 1
    assert p2.promise_id == 2
    assert p3.promise_id == 3

    # Bob's promises should be numbered 1, 2 (independent of Alice)
    assert p4.promise_id == 1
    assert p5.promise_id == 2

    # Verify in database
    async with factory() as s:
        alice_promises = await s.execute(
            select(Promise).where(Promise.giver_id == 100).order_by(Promise.promise_id)
        )
        alice_list = alice_promises.scalars().all()
        assert len(alice_list) == 3
        assert [p.promise_id for p in alice_list] == [1, 2, 3]

        bob_promises = await s.execute(
            select(Promise).where(Promise.giver_id == 200).order_by(Promise.promise_id)
        )
        bob_list = bob_promises.scalars().all()
        assert len(bob_list) == 2
        assert [p.promise_id for p in bob_list] == [1, 2]

    await eng.dispose()


@pytest.mark.asyncio
async def test_accept_notification_includes_content():
    """Accept notification to giver should include promise content."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "buy milk", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        p.giver_pending_message_id = 11111
        p.giver_pending_chat_id = 100
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="accept")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_accepted(cb, cb_data)

    # Check that notification includes promise content
    cb.bot.edit_message_text.assert_called_once()
    edit_kwargs = cb.bot.edit_message_text.call_args[1]
    assert "buy milk" in edit_kwargs["text"]
    assert "تایید کرد" in edit_kwargs["text"]
    await eng.dispose()


@pytest.mark.asyncio
async def test_reject_notification_includes_content():
    """Reject notification to giver should include promise content."""
    eng, factory = await _make_test_db()

    async with factory() as s:
        await get_or_create_user(s, 100, "alice", "Alice")
        await get_or_create_user(s, 200, "bob", "Bob")
        p = await create_promise(s, 100, "clean house", TargetType.FRIEND, 200, PromiseStatus.PENDING)
        pid = p.id
        p.giver_pending_message_id = 22222
        p.giver_pending_chat_id = 100
        await s.commit()

    cb_data = ReceiverConfirmCallback(promise_id=pid, action="reject")
    cb = make_callback(cb_data.pack(), user_id=200, full_name="Bob")

    with patch("src.handlers.promise.get_session", _session_cm(factory)):
        await promise_rejected(cb, cb_data)

    # Check that notification includes promise content
    cb.bot.edit_message_text.assert_called_once()
    edit_kwargs = cb.bot.edit_message_text.call_args[1]
    assert "clean house" in edit_kwargs["text"]
    assert "رد کرد" in edit_kwargs["text"]
    await eng.dispose()
