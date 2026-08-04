"""Scoring service for Promise Bot."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Promise, PromiseStatus, TargetType


# ── Constants ──────────────────────────────────────────────

SCORE_DONE_BASE = 10
SCORE_STREAK_BONUS_PER_STEP = 2
SCORE_STREAK_BONUS_CAP = 10
SCORE_EARLY_BONUS_MAX = 10
SCORE_BROKEN_CONFESSION = -8
SCORE_EXPIRED = -12
SCORE_DISPUTED_PENALTY = -5


# ── Internal Helpers ───────────────────────────────────────

async def _get_user(session: AsyncSession, user_id: int) -> User | None:
    """Get user by telegram_id."""
    stmt = select(User).where(User.telegram_id == user_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


def calculate_early_bonus(deadline, created_at, done_at) -> int:
    """هرچه زودتر از موعد انجام بشه، پاداش بیشتر — نسبت به کل بازه‌ی زمانی."""
    total_window = (deadline - created_at).total_seconds()
    if total_window <= 0:
        return 0
    time_used = (done_at - created_at).total_seconds()
    time_saved_ratio = max(0, 1 - (time_used / total_window))
    return round(time_saved_ratio * SCORE_EARLY_BONUS_MAX)


async def _apply_streak_bonus(user: User) -> int:
    """Calculate and apply streak bonus. Returns bonus amount."""
    if user.current_streak >= 1:
        bonus = min(user.current_streak * SCORE_STREAK_BONUS_PER_STEP, SCORE_STREAK_BONUS_CAP)
        user.score += bonus
        user.current_streak += 1
        return bonus
    else:
        user.current_streak = 1
        return 0


# ── Public API ──────────────────────────────────────────────

async def apply_done_score(session: AsyncSession, user_id: int, promise: Promise) -> None:
    """امتیازدهی برای DONE — فقط برای قول‌های دوطرفه (FRIEND)."""
    if promise.target_type == TargetType.SELF:
        return  # قول‌های شخصی هیچ امتیازی نمی‌گیرن
    
    user = await _get_user(session, user_id)
    if not user:
        return
    
    user.score += SCORE_DONE_BASE
    
    # بونس استریک
    await _apply_streak_bonus(user)
    
    # بونس سرعت متناسب با زمان — فقط اگه deadline داشت
    if promise.deadline and promise.claimed_done_at:
        bonus = calculate_early_bonus(promise.deadline, promise.created_at, promise.claimed_done_at)
        user.score += bonus


async def apply_broken_score(session: AsyncSession, user_id: int, promise: Promise) -> None:
    """جریمه‌ی BROKEN — فقط برای قول‌های دوطرفه."""
    if promise.target_type == TargetType.SELF:
        return
    
    user = await _get_user(session, user_id)
    if user:
        user.score += SCORE_BROKEN_CONFESSION
        user.current_streak = 0


async def apply_expired_score(session: AsyncSession, user_id: int) -> None:
    """جریمه‌ی EXPIRED — همیشه دوطرفه، چون self بدون claim نمی‌ره expired."""
    user = await _get_user(session, user_id)
    if user:
        user.score += SCORE_EXPIRED
        user.current_streak = 0


async def apply_disputed_score(session: AsyncSession, user_id: int) -> None:
    """جریمه‌ی فوری وقتی گیرنده ادعا رو رد می‌کنه."""
    user = await _get_user(session, user_id)
    if user:
        user.score += SCORE_DISPUTED_PENALTY


async def resolve_dispute_to_done(session: AsyncSession, user_id: int, promise: Promise) -> None:
    """گیرنده بعداً نظرش عوض می‌کنه — جبران جریمه‌ی قبلی + امتیاز کامل DONE."""
    user = await _get_user(session, user_id)
    if user:
        user.score -= SCORE_DISPUTED_PENALTY  # خنثی کردن جریمه‌ی قبلی
    await apply_done_score(session, user_id, promise)