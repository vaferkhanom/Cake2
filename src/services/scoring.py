"""Scoring service for Promise Bot."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Promise, PromiseStatus


async def apply_done_score(session: AsyncSession, user_id: int) -> None:
    """Apply scoring when a promise is marked as done."""
    stmt = select(User).where(User.telegram_id == user_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user:
        return
    
    # Increment score
    user.score += 10  # Base score for completing a promise
    
    # Check if last promise was also done for streak
    last_promise_stmt = (
        select(Promise)
        .where(Promise.giver_id == user_id)
        .order_by(Promise.created_at.desc())
        .limit(2)
    )
    last_promise_res = await session.execute(last_promise_stmt)
    last_promises = list(last_promise_res.scalars().all())
    
    if len(last_promises) >= 2:
        # Check if the previous one was also done
        if last_promises[1].status == PromiseStatus.DONE:
            user.current_streak += 1
            user.score += user.current_streak * 2  # Bonus for streak
        else:
            user.current_streak = 1
    else:
        user.current_streak = 1
    
    await session.commit()