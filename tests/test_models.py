import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database.models import Base, User, Promise, TargetType, PromiseStatus

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_creation(db_session: AsyncSession):
    user = User(telegram_id=12345, username="testuser", full_name="Test User")
    db_session.add(user)
    await db_session.commit()

    res = await db_session.get(User, 12345)
    assert res is not None
    assert res.username == "testuser"
    assert res.display_name == "@testuser"

@pytest.mark.asyncio
async def test_promise_creation(db_session: AsyncSession):
    giver = User(telegram_id=1, username="giver", full_name="Giver")
    receiver = User(telegram_id=2, username="receiver", full_name="Receiver")
    db_session.add_all([giver, receiver])
    await db_session.commit()

    promise = Promise(
        content="من قول می‌دهم پروژه را تحویل دهم",
        giver_id=giver.telegram_id,
        receiver_id=receiver.telegram_id,
        target_type=TargetType.FRIEND,
        status=PromiseStatus.PENDING
    )
    db_session.add(promise)
    await db_session.commit()

    assert promise.id is not None
    assert promise.status == PromiseStatus.PENDING
    assert promise.jalali_created_at is not None
