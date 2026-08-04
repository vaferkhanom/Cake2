"""Utility functions for formatting."""

import html
import jdatetime
import zoneinfo
from datetime import datetime, timezone

IRAN_TZ = zoneinfo.ZoneInfo("Asia/Tehran")


def escape_html(text: str) -> str:
    """Escape user-provided text for safe HTML rendering in Telegram."""
    return html.escape(text)


def format_jalali_date(dt: datetime, include_time: bool = True) -> str:
    """تبدیل UTC datetime به رشته‌ی جلالی به وقت تهران."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    tehran_dt = dt.astimezone(IRAN_TZ)
    jd = jdatetime.datetime.fromgregorian(datetime=tehran_dt)
    if include_time:
        return jd.strftime("%Y/%m/%d ساعت %H:%M")
    return jd.strftime("%Y/%m/%d")


def format_jalali_short(dt: datetime) -> str:
    """فقط تاریخ، بدون ساعت — برای دیدلاین‌ها."""
    return format_jalali_date(dt, include_time=False)


def make_mention(user_id: int, name: str) -> str:
    """Create a Telegram mention for a user (HTML-safe)."""
    return f'<a href="tg://user?id={user_id}">{escape_html(name)}</a>'
