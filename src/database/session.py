"""Database session management for Promise Bot."""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, update
from src.config import settings
from src.database.models import Base, User, Promise, PromiseStatus, TargetType


DATABASE_URL = f"sqlite+aiosqlite:///{settings.DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session():
    """Get a database session with automatic commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str) -> User:
    """Get or create user, upgrading stub users to real ones."""
    cleaned_username = username.lstrip("@") if username else None

    user = None
    if telegram_id > 0:
        stmt = select(User).where(User.telegram_id == telegram_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

    if not user and cleaned_username:
        stmt = select(User).where(User.username == cleaned_username)
        res = await session.execute(stmt)
        stub_user = res.scalar_one_or_none()
        if stub_user and stub_user.telegram_id < 0 and telegram_id > 0:
            old_id = stub_user.telegram_id
            await session.execute(
                update(Promise).where(Promise.receiver_id == old_id).values(receiver_id=telegram_id)
            )
            await session.delete(stub_user)
            await session.commit()

            user = User(
                telegram_id=telegram_id,
                username=cleaned_username,
                full_name=full_name,
                has_started_bot=True,
            )
            session.add(user)
            await session.commit()
            return user

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=cleaned_username,
            full_name=full_name,
            has_started_bot=True,
        )
        session.add(user)
    else:
        user.has_started_bot = True
        if telegram_id > 0:
            user.telegram_id = telegram_id
        if cleaned_username:
            user.username = cleaned_username
        user.full_name = full_name

    await session.commit()
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Get user by telegram_id."""
    stmt = select(User).where(User.telegram_id == user_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    """Get user by username."""
    stmt = select(User).where(User.username == username)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def create_stub_user(session: AsyncSession, username: str) -> User:
    """Create a stub user for someone who hasn't started the bot."""
    import random
    stub = User(
        telegram_id=-random.randint(1000000, 9999999),
        username=username,
        full_name=username,
        has_started_bot=False,
    )
    session.add(stub)
    await session.commit()
    await session.refresh(stub)
    return stub


async def create_promise(
    session: AsyncSession,
    giver_id: int,
    content: str,
    target_type: TargetType,
    receiver_id: int | None,
    status: PromiseStatus,
    deadline: str | None = None,
) -> Promise:
    """Create a new promise and assign promise_id."""
    from sqlalchemy import func

    # Get next promise_id
    stmt = select(func.max(Promise.promise_id))
    res = await session.execute(stmt)
    max_id = res.scalar()
    promise_id = (max_id or 0) + 1

    promise = Promise(
        promise_id=promise_id,
        content=content,
        giver_id=giver_id,
        receiver_id=receiver_id,
        target_type=target_type,
        status=status,
        deadline=deadline,
    )
    session.add(promise)
    await session.commit()
    await session.refresh(promise)
    return promise


async def update_promise_status(session: AsyncSession, promise_id: int, status: PromiseStatus) -> Promise | None:
    """Update promise status."""
    stmt = select(Promise).where(Promise.id == promise_id)
    res = await session.execute(stmt)
    promise = res.scalar_one_or_none()
    if promise:
        promise.status = status
        await session.commit()
        await session.refresh(promise)
    return promise