import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.database.models import Base, User, Promise, TargetType, PromiseStatus
from src.handlers.promise import (
    process_initial_confirm,
    process_target_selection,
    process_promise_approval,
    get_or_create_user
)

@pytest.mark.asyncio
async def test_get_or_create_user_username_matching():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_maker() as session:
        # Create a giver user first
        giver = User(telegram_id=1001, username="giver_user", full_name="Giver")
        session.add(giver)

        # Create stub user with negative ID
        stub_user = User(telegram_id=-123456, username="my_friend", full_name="my_friend", has_started_bot=False)
        session.add(stub_user)
        await session.commit()

        # Create a Promise pointing to the stub negative ID
        promise = Promise(
            content="تست قول",
            giver_id=1001,
            receiver_id=-123456,
            target_type=TargetType.FRIEND,
            status=PromiseStatus.PENDING,
        )
        session.add(promise)
        await session.commit()

        # Real user starts bot with positive telegram_id
        real_user = await get_or_create_user(session, telegram_id=999888, username="my_friend", full_name="Real Friend")
        
        assert real_user.telegram_id == 999888
        assert real_user.username == "my_friend"
        assert real_user.has_started_bot is True

        # Check promise receiver_id is updated to real positive ID
        await session.refresh(promise)
        assert promise.receiver_id == 999888

    await engine.dispose()

@pytest.mark.asyncio
async def test_handler_initial_confirm_no():
    callback = MagicMock()
    callback.data = "confirm_initial:no:1001"
    callback.from_user.id = 1001
    callback.message = AsyncMock()

    state = AsyncMock()

    await process_initial_confirm(callback, state)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once_with("عملیات لغو شد.")

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
        callback.message.edit_text.assert_awaited_once_with("قول شما ثبت شد")
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
                content="انجام پروژه",
                giver_id=giver.telegram_id,
                receiver_id=receiver.telegram_id,
                target_type=TargetType.FRIEND,
                status=PromiseStatus.PENDING
            )
            session.add(promise)
            await session.commit()
            promise_id = promise.id

        callback = MagicMock()
        callback.data = f"promise_appr:yes:{promise_id}:2002"
        callback.from_user.id = 2002
        callback.message = AsyncMock()
        callback.bot = AsyncMock()

        await process_promise_approval(callback)

        callback.message.edit_text.assert_awaited_once_with("تایید شد")
        callback.bot.send_message.assert_awaited()
    finally:
        p_mod.AsyncSessionLocal = original_session_local
        await engine.dispose()
