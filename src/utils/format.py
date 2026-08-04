"""Utility functions for formatting."""

import jdatetime
from datetime import datetime, timezone


def format_jalali_date(dt: datetime) -> str:
    """Format datetime to Jalali string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    jd = jdatetime.datetime.fromgregorian(datetime=dt, timezone=dt.tzinfo)
    return jd.strftime("%Y/%m/%d ساعت %H:%M")


def make_mention(user_id: int, name: str) -> str:
    """Create a Telegram mention for a user."""
    return f'<a href="tg://user?id={user_id}">{name}</a>'