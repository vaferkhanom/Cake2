import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from src.database.models import Base, User, Promise, TargetType, PromiseStatus
from src.handlers.promise import (
    process_initial_confirm,
    process_target_selection,
    process_promise_approval,
    get_or_create_user,
    group_promise_command,
    process_promise_status_change
)

@pytest.mark.asyncio
async def test_get_or_create_user_username_matching():
    """Test that when a real user starts the bot with a username that matches a stub user,
    the stub is merged and existing promises pointing to the stub's negative ID are updated."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        # 1. Giver creates a promise for a friend who hasn't started the bot
        #    This creates a stub user with negative ID
        stub_user = User(telegram_id=-123456, username="my_friend", full_name="my_friend", has_started_bot=False)
        session.add(stub_user)
        await session.commit()

        # 2. Giver creates a promise pointing to the stub's negative ID
        promise = Promise(
            content="تست قول",
            giver_id=1001,
            receiver_id=-123456,  # Points to stub
            target_type=TargetType.FRIEND,
            status=PromiseStatus.PENDING,
        )
        session.add(promise)
        await session.commit()

        # 3. Real user (the friend) starts the bot with the same username
        #    This should merge the stub and update the promise's receiver_id
        real_user = await get_or_create_user(session, telegram_id=999888, username="my_friend", full_name="Real Friend")
        
        assert real_user.telegram_id == 999888
        assert real_user.username == "my_friend"
        assert real_user.has_started_bot is True

        # 4. Check that the promise's receiver_id was updated from negative stub ID to real positive ID
        stmt = select(Promise).where(Promise.id == promise.id)
        res = await session.execute(stmt)
        updated_promise = res.scalar_one_or_none()
        assert updated_promise is not None
        assert updated_promise.receiver_id == 999888

    await engine.dispose()

@pytest.mark.asyncio
async def test_handler_initial_confirm_no():
    callback = MagicMock()
    callback.data = "confirm_initial:no:1001"
    callback.from_user.id = 1001
    callback.message = AsyncMock()

    state = AsyncMock()

    await process_initial_confirm(callback, state)

    # New behavior: goes back to waiting_for_content, not clear
    state.set_state.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once_with("باشه، دوباره بگو 🙂")

@pytest.mark.asyncio
async def test_handler_target_selection_self():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import src.handlers.promise as p_mod
    original_session_local = p_mod.AsyncSessionLocal
    p_mod.AsyncSessionLocal = session_maker

    try:
        callback = MagicMock()
        callback.data = "target:self:1001"
        callback.from_user.id = 1001
        callback.from_user.username = "test_giver"
        callback.from_user.full_name = "Test Giver"
        callback.message = AsyncMock()

        state = AsyncMock()
        state.get_data.return_value = {"content": "خرید کتاب"}

        await process_target_selection(callback, state)

        state.clear.assert_awaited_once()
        # New message includes promise_id and new tone
        callback.message.edit_text.assert_awaited_once()
        call_args = callback.message.edit_text.call_args[0][0]
        assert "ثبت شد ✅" in call_args
        assert "موفق باشی 💪" in call_args
        assert "قول #" in call_args
    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()

@pytest.mark.asyncio
async def test_handler_promise_approval_yes():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import src.handlers.promise as p_mod
    original_session_local = p_mod.AsyncSessionLocal
    p_mod.AsyncSessionLocal = session_maker

    try:
        async with session_maker() as session:
            giver = User(telegram_id=1001, username="giver", full_name="Giver")
            receiver = User(telegram_id=2002, username="receiver", full_name="Receiver")
            session.add_all([giver, receiver])
            await session.commit()

            promise = Promise(
                promise_id=123,
                content="انجام پروژه",
                giver_id=giver.telegram_id,
                receiver_id=receiver.telegram_id,
                target_type=TargetType.FRIEND,
                status=PromiseStatus.PENDING
            )
            session.add(promise)
            await session.commit()

        callback = MagicMock()
        callback.data = f"promise_appr:yes:123:2002"  # Using promise_id=123
        callback.from_user.id = 2002
        callback.message = AsyncMock()
        callback.bot = AsyncMock()

        await process_promise_approval(callback)

        callback.message.edit_text.assert_awaited_once_with("قبولش کردی ✅ حالا یادت باشه ها 😉")
        callback.bot.send_message.assert_awaited()
    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()

# New tests for Phase 2 features
@pytest.mark.asyncio
async def test_promise_id_assignment():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import src.handlers.promise as p_mod
    original_session_local = p_mod.AsyncSessionLocal
    p_mod.AsyncSessionLocal = session_maker

    try:
        async with session_maker() as session:
            user = User(telegram_id=1001, username="test", full_name="Test")
            session.add(user)
            await session.commit()

            # First promise should get promise_id=1
            pid1 = await p_mod.get_next_promise_id(session)
            p1 = Promise(promise_id=pid1, content="first", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.CONFIRMED)
            session.add(p1)
            await session.commit()

            # Second promise should get promise_id=2
            pid2 = await p_mod.get_next_promise_id(session)
            p2 = Promise(promise_id=pid2, content="second", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.CONFIRMED)
            session.add(p2)
            await session.commit()

            assert p1.promise_id == 1
            assert p2.promise_id == 2
    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()

@pytest.mark.asyncio
async def test_credibility_score_zero_denominator():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        user = User(telegram_id=1001, username="test", full_name="Test")
        session.add(user)
        
        # Only confirmed promises, no done/broken
        p1 = Promise(promise_id=1, content="pending1", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.CONFIRMED)
        p2 = Promise(promise_id=2, content="pending2", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.CONFIRMED)
        session.add_all([p1, p2])
        await session.commit()

        # Check counts
        from sqlalchemy import select, func
        done_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == 1001,
            Promise.status == PromiseStatus.DONE
        )
        done_res = await session.execute(done_stmt)
        done_count = done_res.scalar() or 0
        
        broken_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == 1001,
            Promise.status == PromiseStatus.BROKEN
        )
        broken_res = await session.execute(broken_stmt)
        broken_count = broken_res.scalar() or 0

        assert done_count == 0
        assert broken_count == 0
        # denominator would be 0, handled in handler

    await engine.dispose()

@pytest.mark.asyncio
async def test_credibility_score_calculation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        user = User(telegram_id=1001, username="test", full_name="Test")
        session.add(user)
        
        p1 = Promise(promise_id=1, content="done1", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.DONE)
        p2 = Promise(promise_id=2, content="done2", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.DONE)
        p3 = Promise(promise_id=3, content="broken1", giver_id=1001, target_type=TargetType.SELF, status=PromiseStatus.BROKEN)
        session.add_all([p1, p2, p3])
        await session.commit()

        from sqlalchemy import select, func
        done_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == 1001,
            Promise.status == PromiseStatus.DONE
        )
        done_res = await session.execute(done_stmt)
        done_count = done_res.scalar() or 0
        
        broken_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == 1001,
            Promise.status == PromiseStatus.BROKEN
        )
        broken_res = await session.execute(broken_stmt)
        broken_count = broken_res.scalar() or 0

        assert done_count == 2
        assert broken_count == 1
        # 2/(2+1) = 66.6...% -> 67%
        pct = round((done_count / (done_count + broken_count)) * 100)
        assert pct == 67

    await engine.dispose()

# --- NEW TESTS FOR PHASE 2 ---

@pytest.mark.asyncio
async def test_group_promise_command_with_mention():
    """Test /promise @username text in group chat"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import src.handlers.promise as p_mod
    original_session_local = p_mod.AsyncSessionLocal
    p_mod.AsyncSessionLocal = session_maker

    try:
        async with session_maker() as session:
            giver = User(telegram_id=1001, username="giver", full_name="Giver")
            receiver = User(telegram_id=2002, username="receiver", full_name="Receiver")
            session.add_all([giver, receiver])
            await session.commit()

        message = MagicMock()
        message.chat.type = "group"
        message.text = "/promise @receiver قول میدم فردا بستنی بخرم"
        message.from_user.id = 1001
        message.from_user.username = "giver"
        message.from_user.full_name = "Giver"
        message.reply_to_message = None
        message.bot = AsyncMock()
        message.answer = AsyncMock()
        message.reply = AsyncMock()

        state = AsyncMock()

        await group_promise_command(message, state)

        # Should have tried to send DM or group notification
        message.bot.send_message.assert_awaited()
        message.answer.assert_awaited()

    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()

@pytest.mark.asyncio
async def test_group_promise_command_with_reply():
    """Test /promise text as reply to friend's message in group chat"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import src.handlers.promise as p_mod
    original_session_local = p_mod.AsyncSessionLocal
    p_mod.AsyncSessionLocal = session_maker

    try:
        async with session_maker() as session:
            giver = User(telegram_id=1001, username="giver", full_name="Giver")
            receiver = User(telegram_id=2002, username="receiver", full_name="Receiver")
            session.add_all([giver, receiver])
            await session.commit()

        message = MagicMock()
        message.chat.type = "group"
        message.text = "/promise قول میدم فردا بستنی بخرم"
        message.from_user.id = 1001
        message.from_user.username = "giver"
        message.from_user.full_name = "Giver"
        
        # Mock reply_to_message
        reply_msg = MagicMock()
        reply_msg.from_user.id = 2002
        reply_msg.from_user.username = "receiver"
        reply_msg.from_user.is_bot = False
        message.reply_to_message = reply_msg
        
        message.bot = AsyncMock()
        message.answer = AsyncMock()
        message.reply = AsyncMock()

        state = AsyncMock()

        await group_promise_command(message, state)

        # Should have tried to send DM or group notification
        message.bot.send_message.assert_awaited()
        message.answer.assert_awaited()

    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()

@pytest.mark.asyncio
async def test_only_giver_can_change_promise_status():
    """Test that only the giver can trigger done/broken status change"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import src.handlers.promise as p_mod
    original_session_local = p_mod.AsyncSessionLocal
    p_mod.AsyncSessionLocal = session_maker

    try:
        async with session_maker() as session:
            giver = User(telegram_id=1001, username="giver", full_name="Giver")
            receiver = User(telegram_id=2002, username="receiver", full_name="Receiver")
            session.add_all([giver, receiver])
            await session.commit()

            promise = Promise(
                promise_id=456,
                content="انجام پروژه",
                giver_id=giver.telegram_id,
                receiver_id=receiver.telegram_id,
                target_type=TargetType.FRIEND,
                status=PromiseStatus.CONFIRMED
            )
            session.add(promise)
            await session.commit()

        # Test 1: Receiver tries to change status (should be rejected)
        # Callback data includes the REAL giver_id (1001) but the receiver (2002) tries to press it
        callback_receiver = MagicMock()
        callback_receiver.data = f"promise_status:done:456:1001"  # giver_id=1001 in callback data
        callback_receiver.from_user.id = 2002  # receiver trying to change
        callback_receiver.message = AsyncMock()
        callback_receiver.answer = AsyncMock()

        await p_mod.process_promise_status_change(callback_receiver)

        # Should reject with alert
        callback_receiver.answer.assert_awaited_once()
        call_args = callback_receiver.answer.call_args
        assert "فقط قول‌دهنده" in call_args[0][0] or "فقط قول‌دهنده" in str(call_args)

        # Verify status didn't change
        async with session_maker() as session:
            stmt = select(Promise).where(Promise.promise_id == 456)
            res = await session.execute(stmt)
            p = res.scalar_one_or_none()
            assert p.status == PromiseStatus.CONFIRMED

        # Test 2: Giver tries to change status (should succeed)
        callback_giver = MagicMock()
        callback_giver.data = f"promise_status:done:456:1001"  # giver_id in callback
        callback_giver.from_user.id = 1001  # giver
        callback_giver.message = AsyncMock()
        callback_giver.answer = AsyncMock()

        await p_mod.process_promise_status_change(callback_giver)

        # Should succeed and update message
        callback_giver.message.edit_text.assert_awaited_once()
        call_args = callback_giver.message.edit_text.call_args[0][0]
        assert "🏆" in call_args  # done emoji
        assert "انجام شده" in call_args

        # Verify status changed in DB
        async with session_maker() as session:
            stmt = select(Promise).where(Promise.promise_id == 456)
            res = await session.execute(stmt)
            p = res.scalar_one_or_none()
            assert p.status == PromiseStatus.DONE

    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()