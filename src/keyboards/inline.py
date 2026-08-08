"""Inline keyboards and callback data for Promise Bot."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from src.config import settings
from src.utils.format import escape_html

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


class BrokenCallback(CallbackData, prefix="brk"):
    promise_id: int


class ResolveDisputeCallback(CallbackData, prefix="rdp"):
    promise_id: int


class BackCallback(CallbackData, prefix="back"):
    target_state: str  # state to go back to


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


# ── Back button helper ──────────────────────────────────────


def back_button(target_state: str, text: str = "🔙 برگشت") -> InlineKeyboardButton:
    """Create a back button for FSM navigation."""
    return InlineKeyboardButton(
        text=text,
        callback_data=BackCallback(target_state=target_state).pack(),
    )


def back_keyboard(target_state: str, text: str = "🔙 برگشت") -> InlineKeyboardMarkup:
    """Single back button keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=BackCallback(target_state=target_state).pack())
    return builder.as_markup()


def confirm_keyboard_with_back():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ بزن بریم", callback_data=ConfirmPromiseCallback(action="yes").pack())
    builder.button(text="✏️ عوضش کنم", callback_data=ConfirmPromiseCallback(action="edit").pack())
    builder.adjust(2)
    builder.row(back_button("waiting_for_content"))
    return builder.as_markup()


def deadline_choice_keyboard_with_back():
    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 فردا", callback_data=DeadlineCallback(action="tomorrow").pack())
    builder.button(text="📅 این هفته", callback_data=DeadlineCallback(action="week").pack())
    builder.button(text="🗓 این ماه", callback_data=DeadlineCallback(action="month").pack())
    builder.button(text="⏭ بدون مهلت", callback_data=DeadlineCallback(action="none").pack())
    builder.button(text="✏️ تاریخ دلخواه", callback_data=DeadlineCallback(action="custom").pack())
    builder.adjust(2, 2, 1)
    builder.row(back_button("waiting_for_confirmation"))
    return builder.as_markup()


def target_keyboard_with_back():
    builder = InlineKeyboardBuilder()
    builder.button(text="🙋‍♂️ خودم", callback_data=TargetCallback(target="self").pack())
    builder.button(text="🤍 یکی از دوستام", callback_data=TargetCallback(target="friend").pack())
    builder.adjust(2)
    builder.row(back_button("waiting_for_deadline_choice"))
    return builder.as_markup()


def friend_id_keyboard_with_back():
    builder = InlineKeyboardBuilder()
    builder.row(back_button("waiting_for_target", "🔙 برگشت به انتخاب هدف"))
    return builder.as_markup()


def deadline_value_keyboard_with_back():
    builder = InlineKeyboardBuilder()
    builder.row(back_button("waiting_for_deadline_choice", "🔙 برگشت به انتخاب مهلت"))
    return builder.as_markup()


# ── Helper Functions ───────────────────────────────────────

PAGE_SIZE = 4  # 2x2 grid


def get_status_emoji(status) -> str:
    """Single source of truth for promise status emoji (grid + detail card + model)."""
    from src.database.models import PromiseStatus
    mapping = {
        PromiseStatus.PENDING: "⏳",
        PromiseStatus.CONFIRMED: "✅",
        PromiseStatus.CLAIMED_DONE: "⏳",
        PromiseStatus.DONE: "🎉",
        PromiseStatus.BROKEN: "💔",
        PromiseStatus.DISPUTED: "⚠️",
        PromiseStatus.EXPIRED: "⏰",
    }
    return mapping.get(status, "")


def get_status_text(status) -> str:
    """Single source of truth for promise status display text."""
    from src.database.models import PromiseStatus
    mapping = {
        PromiseStatus.PENDING: "در انتظار تایید",
        PromiseStatus.CONFIRMED: "تایید شده",
        PromiseStatus.CLAIMED_DONE: "در انتظار تایید طرف مقابل",
        PromiseStatus.DONE: "انجام شده",
        PromiseStatus.BROKEN: "نقض شده",
        PromiseStatus.DISPUTED: "مخالفیت شده",
        PromiseStatus.EXPIRED: "منقضی شده",
    }
    return mapping.get(status, "")


def short_title(content: str, max_len: int = 24) -> str:
    """Truncate promise content for button label."""
    if len(content) <= max_len:
        return content
    return content[:max_len - 1] + "…"


def format_promise_card(promise, user_id: int) -> str:
    """Format full promise detail card."""
    from src.utils.format import format_jalali_date, format_jalali_short

    emoji = get_status_emoji(promise.status)
    text = get_status_text(promise.status)

    lines = [
        f"<b>#{promise.promise_id or promise.id}</b> · {emoji} {text}",
        f"💬 {escape_html(promise.content)}",
    ]

    if promise.target_type.value == "self":
        lines.append("👤 برای: خودم")
    else:
        if promise.giver_id == user_id:
            receiver_name = escape_html(promise.receiver.display_name) if promise.receiver else "دوست"
            lines.append(f"👤 به: {receiver_name}")
        else:
            giver_name = escape_html(promise.giver.display_name) if promise.giver else "دوست"
            lines.append(f"👤 از: {giver_name}")

    lines.append(f"🗓 {format_jalali_date(promise.created_at)}")

    if promise.deadline:
        lines.append(f"⏰ مهلت: {format_jalali_short(promise.deadline)}")

    return "\n".join(lines)


def get_status_button_emoji(status) -> str:
    """Get emoji for promise status on grid buttons — delegates to shared function."""
    return get_status_emoji(status)


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
    
    # Fixed back-to-menu row (always present)
    builder.row(InlineKeyboardButton(
        text="🔙 بازگشت به منوی اصلی",
        callback_data="main:back",
    ))
    
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


def get_promise_detail_keyboard(promise, user_id: int, list_type: str, page: int):
    """Keyboard for promise detail view with action buttons based on status and user role + back to list."""
    from src.database.models import PromiseStatus
    
    builder = InlineKeyboardBuilder()
    is_giver = promise.giver_id == user_id

    # Action buttons based on status and user role
    if promise.status == PromiseStatus.CONFIRMED and is_giver:
        # Only giver can claim done or admit broken on CONFIRMED promises
        builder.button(text="🏁 انجامش دادم", callback_data=ClaimDoneCallback(promise_id=promise.id, action="claim_done").pack())
        builder.button(text="💔 نشد که نشد", callback_data=BrokenCallback(promise_id=promise.id).pack())
    elif promise.status == PromiseStatus.CLAIMED_DONE and not is_giver:
        # Only receiver can confirm or dispute on CLAIMED_DONE
        builder.button(text="✅ بله انجام داده", callback_data=ReceiverConfirmDoneCallback(promise_id=promise.id, action="confirm_done").pack())
        builder.button(text="❌ نه انجام نداده", callback_data=ReceiverConfirmDoneCallback(promise_id=promise.id, action="dispute").pack())
    elif promise.status == PromiseStatus.DISPUTED and not is_giver:
        # Receiver can resolve dispute
        builder.button(text="🔄 در واقع تایید می‌کنم", callback_data=ResolveDisputeCallback(promise_id=promise.id).pack())
    # For other statuses (DONE, BROKEN, EXPIRED, PENDING, REJECTED, or CLAIMED_DONE for giver)
    # no action buttons shown

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
