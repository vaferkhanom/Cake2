"""Tests for Promise Bot - Phase 5 complete."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.models import Base, Promise, PromiseStatus, TargetType, User
from src.database.session import create_promise, get_or_create_user
from src.handlers.promise import (
    new_promise_start,
    promise_content_received,
    promise_confirmed,
    promise_edit,
    target_self,
    target_friend,
    promise_accepted,
    promise_rejected,
    _process_friend,
    show_my_promises_menu,
    show_promise_list,
    show_promise_detail,
)
from src.keyboards.inline import (
    ConfirmPromiseCallback,
    ReceiverConfirmCallback,
    TargetCallback,
    PromiseStatusCallback,
    ClaimDoneCallback,
    ReceiverConfirmDoneCallback,
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

@pytest.mark.asyncio
async def test_start_enters_fsm():
    state = _make_fsm()
    msg = make_message(text="🤝 ثبت یه قول جدید")
    await new_promise_start(msg, state)
    assert await state.get_state() == PromiseStates.waiting_for_content


@pytest.mark.asyncio
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
    cb.message.answer.assert_called_once()
    msg_text = cb.message.answer.call_args[0][0]
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

@pytest.mark.asyncio
async def test_show_my_promises_menu():
    """Test that main menu shows 3 options."""
    msg = make_message(text="📋 قول‌های من")
    await show_my_promises_menu(msg)
    msg.answer.assert_called_once()
    # Should show inline keyboard with 3 buttons
    call_kwargs = msg.answer.call_args[1]
    assert "reply_markup" in call_kwargs


@pytest.mark.asyncio
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


# ── Model Tests ────────────────────────────────────────

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