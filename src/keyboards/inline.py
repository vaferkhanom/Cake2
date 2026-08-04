"""Inline keyboards and callback data for Promise Bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from src.config import settings


# ── Callback Data Classes ──────────────────────────────────

class ConfirmPromiseCallback(CallbackData, prefix="cpr"):
    action: str  # "yes" | "edit"


class ReceiverConfirmCallback(CallbackData, prefix="rapp"):
    promise_id: int
    action: str  # "accept" | "reject"


class TargetCallback(CallbackData, prefix="tgt"):
    target: str  # "self" | "friend"


class PromiseStatusCallback(CallbackData, prefix="pst"):
    promise_id: int
    action: str  # "done" | "broken"
    giver_id: int


class ClaimDoneCallback(CallbackData, prefix="clm"):
    promise_id: int
    action: str  # "claim_done"


class ReceiverConfirmDoneCallback(CallbackData, prefix="rcd"):
    promise_id: int
    action: str  # "confirm_done" | "dispute"


class DeadlineCallback(CallbackData, prefix="dl"):
    action: str  # "tomorrow" | "week" | "month" | "none" | "custom"


# Phase 5: Pagination callbacks
class PromiseListCallback(CallbackData, prefix="plist"):
    list_type: str  # "self" | "given" | "received"
    page: int


class PromiseItemCallback(CallbackData, prefix="pitem"):
    promise_id: int
    list_type: str  # "self" | "given" | "received"
    page: int


# ── Helper Functions ───────────────────────────────────────

PAGE_SIZE = 4  # 2x2 grid


def short_title(content: str, max_len: int = 24) -> str:
    """Truncate promise content for button label."""
    if len(content) <= max_len:
        return content
    return content[:max_len - 1] + "…"


def format_promise_card(promise, user_id: int) -> str:
    """Format full promise detail card."""
    from src.database.models import PromiseStatus
    
    status_emoji = {
        PromiseStatus.PENDING: "⏳",
        PromiseStatus.CONFIRMED: "✅",
        PromiseStatus.REJECTED: "❌",
        PromiseStatus.CLAIMED_DONE: "⏳",
        PromiseStatus.DONE: "🏆",
        PromiseStatus.DISPUTED: "⚠️",
        PromiseStatus.BROKEN: "💔",
        PromiseStatus.EXPIRED: "⏰",
    }
    
    status_text = {
        PromiseStatus.PENDING: "در انتظار تایید",
        PromiseStatus.CONFIRMED: "تایید شده",
        PromiseStatus.REJECTED: "رد شده",
        PromiseStatus.CLAIMED_DONE: "در انتظار تایید طرف مقابل",
        PromiseStatus.DONE: "انجام شده",
        PromiseStatus.DISPUTED: "مخالفیت شده",
        PromiseStatus.BROKEN: "نقض شده",
        PromiseStatus.EXPIRED: "منقضی شده",
    }
    
    emoji = status_emoji.get(promise.status, "")
    text = status_text.get(promise.status, "")
    
    lines = [
        f"<b>#{promise.promise_id or promise.id}</b> · {emoji} {text}",
        f"💬 {promise.content}",
    ]
    
    if promise.target_type.value == "self":
        lines.append("👤 برای: خودم")
    else:
        if promise.giver_id == user_id:
            lines.append(f"👤 به: {promise.receiver.display_name if promise.receiver else 'دوست'}")
        else:
            lines.append(f"👤 از: {promise.giver.display_name if promise.giver else 'دوست'}")
    
    import jdatetime
    jd = jdatetime.datetime.fromtimestamp(promise.created_at.timestamp())
    lines.append(f"🗓 {jd.strftime('%Y/%m/%d ساعت %H:%M')}")
    
    if promise.deadline:
        jdl = jdatetime.datetime.fromgregorian(datetime=promise.deadline, timezone=promise.deadline.tzinfo)
        lines.append(f"⏰ مهلت: {jdl.strftime('%Y/%m/%d')}")
    
    return "\n".join(lines)


def get_status_button_emoji(status) -> str:
    """Get emoji for promise status on grid buttons."""
    from src.database.models import PromiseStatus
    if status in (PromiseStatus.CONFIRMED, PromiseStatus.DONE):
        return "✅"
    elif status in (PromiseStatus.CLAIMED_DONE, PromiseStatus.PENDING):
        return "⏳"
    elif status in (PromiseStatus.BROKEN, PromiseStatus.REJECTED, PromiseStatus.DISPUTED):
        return "💔"
    elif status == PromiseStatus.EXPIRED:
        return "⏰"
    return "⏳"


# ── Main Menu ──────────────────────────────────────────────

def get_main_reply_keyboard():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=settings.MENU_OPTIONS["CREATE_PROMISE"]))
    builder.add(KeyboardButton(text=settings.MENU_OPTIONS["LIST_PROMISES"]))
    builder.add(KeyboardButton(text=settings.MENU_OPTIONS["PROFILE"]))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


# ── FSM Keyboards ──────────────────────────────────────────

def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ بزن بریم", callback_data=ConfirmPromiseCallback(action="yes").pack())
    builder.button(text="✏️ عوضش کنم", callback_data=ConfirmPromiseCallback(action="edit").pack())
    builder.adjust(2)
    return builder.as_markup()


def target_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🙋‍♂️ خودم", callback_data=TargetCallback(target="self").pack())
    builder.button(text="🤍 یکی از دوستام", callback_data=TargetCallback(target="friend").pack())
    builder.adjust(2)
    return builder.as_markup()


def receiver_confirm_keyboard(promise_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ قبوله", callback_data=ReceiverConfirmCallback(promise_id=promise_id, action="accept").pack())
    builder.button(text="❌ نه بابا", callback_data=ReceiverConfirmCallback(promise_id=promise_id, action="reject").pack())
    builder.adjust(2)
    return builder.as_markup()


def deadline_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 فردا", callback_data=DeadlineCallback(action="tomorrow").pack())
    builder.button(text="📅 این هفته", callback_data=DeadlineCallback(action="week").pack())
    builder.button(text="🗓 این ماه", callback_data=DeadlineCallback(action="month").pack())
    builder.button(text="⏭ بدون مهلت", callback_data=DeadlineCallback(action="none").pack())
    builder.button(text="✏️ تاریخ دلخواه", callback_data=DeadlineCallback(action="custom").pack())
    builder.adjust(2, 2, 1)
    return builder.as_markup()


# ── Promise Action Keyboards ──────────────────────────────

def claim_done_keyboard(promise_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏁 انجامش دادم", callback_data=ClaimDoneCallback(promise_id=promise_id, action="claim_done").pack())
    builder.button(text="💔 نشد که نشد", callback_data=PromiseStatusCallback(promise_id=promise_id, action="broken", giver_id=0).pack())
    builder.adjust(2)
    return builder.as_markup()


def receiver_confirm_done_keyboard(promise_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ بله انجام داده", callback_data=ReceiverConfirmDoneCallback(promise_id=promise_id, action="confirm_done").pack())
    builder.button(text="❌ نه انجام نداده", callback_data=ReceiverConfirmDoneCallback(promise_id=promise_id, action="dispute").pack())
    builder.adjust(2)
    return builder.as_markup()


def promise_status_keyboard(promise_id: int, giver_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏆 انجامش دادم", callback_data=PromiseStatusCallback(promise_id=promise_id, action="done", giver_id=giver_id).pack())
    builder.button(text="💔 نشد که نشد", callback_data=PromiseStatusCallback(promise_id=promise_id, action="broken", giver_id=giver_id).pack())
    builder.adjust(2)
    return builder.as_markup()


# ── Phase 5: Promise List Grid ─────────────────────────────

def get_my_promises_menu_keyboard():
    """Top-level 'My Promises' menu with 3 options."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🙋 قول‌های شخصی من", callback_data=PromiseListCallback(list_type="self", page=0).pack())
    builder.button(text="📤 قول‌های من به بقیه", callback_data=PromiseListCallback(list_type="given", page=0).pack())
    builder.button(text="📥 قول‌های بقیه به من", callback_data=PromiseListCallback(list_type="received", page=0).pack())
    builder.adjust(1, 2)
    return builder.as_markup()


def get_promise_list_keyboard(promises: list, list_type: str, page: int, total_count: int):
    """Build 2x2 grid keyboard for promise list page."""
    builder = InlineKeyboardBuilder()
    
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(promises))
    page_promises = promises[start:end]
    
    # Add promise buttons (2x2 grid)
    for promise in page_promises:
        emoji = get_status_button_emoji(promise.status)
        title = short_title(promise.content)
        builder.button(
            text=f"{emoji} {title}",
            callback_data=PromiseItemCallback(promise_id=promise.id, list_type=list_type, page=page).pack()
        )
    
    builder.adjust(2)
    
    # Navigation row
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="◀️ قبلی",
                    callback_data=PromiseListCallback(list_type=list_type, page=page - 1).pack()
                )
            )
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="بعدی ▶️",
                    callback_data=PromiseListCallback(list_type=list_type, page=page + 1).pack()
                )
            )
        if nav_buttons:
            builder.row(*nav_buttons)
    
    return builder.as_markup()


def get_promise_list_header(list_type: str, page: int, total_count: int) -> str:
    """Generate header text for promise list page."""
    titles = {
        "self": "🙋 قول‌های شخصی من",
        "given": "📤 قول‌های من به بقیه",
        "received": "📥 قول‌های بقیه به من",
    }
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    return (
        f"{titles.get(list_type, 'قول‌ها')}\n"
        f"صفحه {page + 1} از {total_pages}  ·  {total_count} قول\n\n"
        f"روی هرکدوم بزن تا جزئیاتش رو ببینی 👇"
    )


def get_promise_detail_keyboard(promise_id: int, giver_id: int, list_type: str, page: int):
    """Keyboard for promise detail view with action buttons + back to list."""
    builder = InlineKeyboardBuilder()
    
    # Action buttons based on status (will be filtered in handler)
    builder.button(text="🏆 انجامش دادم", callback_data=PromiseStatusCallback(promise_id=promise_id, action="done", giver_id=giver_id).pack())
    builder.button(text="💔 نشد که نشد", callback_data=PromiseStatusCallback(promise_id=promise_id, action="broken", giver_id=giver_id).pack())
    
    # Back to list button
    builder.button(
        text="🔙 بازگشت به لیست",
        callback_data=PromiseListCallback(list_type=list_type, page=page).pack()
    )
    
    builder.adjust(2, 1)
    return builder.as_markup()


def get_promise_detail_keyboard_for_receiver(promise_id: int, list_type: str, page: int):
    """Keyboard for receiver viewing a promise detail."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 بازگشت به لیست",
        callback_data=PromiseListCallback(list_type=list_type, page=page).pack()
    )
    builder.adjust(1)
    return builder.as_markup()