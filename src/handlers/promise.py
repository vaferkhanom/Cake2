"""Handlers for promise registration flow (FSM-based) - Complete with Phase 4 & 5."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from src.database.models import Promise, PromiseStatus, TargetType, User
from src.database.session import (
    create_promise,
    create_stub_user,
    get_session,
    get_user_by_id,
    get_user_by_username,
    get_or_create_user,
)
from src.domain import promise_actions as pa
from src.notifications.telegram import TelegramNotifier
from src.utils.format import escape_html, format_jalali_date, format_jalali_short, make_mention
from src.keyboards.inline import (
    ConfirmPromiseCallback,
    ReceiverConfirmCallback,
    TargetCallback,
    ClaimDoneCallback,
    ReceiverConfirmDoneCallback,
    BrokenCallback,
    ResolveDisputeCallback,
    DeadlineCallback,
    PromiseListCallback,
    PromiseItemCallback,
    BackCallback,
    confirm_keyboard,
    confirm_keyboard_with_back,
    claim_done_keyboard,
    receiver_confirm_done_keyboard,
    receiver_confirm_keyboard,
    target_keyboard,
    target_keyboard_with_back,
    deadline_choice_keyboard,
    deadline_choice_keyboard_with_back,
    deadline_value_keyboard_with_back,
    friend_id_keyboard_with_back,
    back_keyboard,
    get_my_promises_menu_keyboard,
    get_promise_list_keyboard,
    get_promise_list_header,
    get_promise_detail_keyboard,
    format_promise_card,
)
from src.services.scoring import (
    apply_done_score,
    apply_broken_score,
    apply_disputed_score,
    resolve_dispute_to_done,
)
from src.states.promise import PromiseStates, GroupPromiseStates

router = Router()
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────

async def send_pending_notifications(bot, session, user: User) -> None:
    """Send pending promise notifications to user on startup."""
    stmt = (
        select(Promise)
        .where(Promise.receiver_id == user.telegram_id, Promise.status == PromiseStatus.PENDING)
        .options(selectinload(Promise.giver))
    )
    res = await session.execute(stmt)
    promises = res.scalars().all()

    for promise in promises:
        giver_name = promise.giver.display_name if promise.giver else "یک کاربر"
        msg_text = (
            f"{make_mention(promise.giver_id, giver_name)} 🫵 می‌خواد بهت یه قول بده:\n"
            f"<blockquote>{escape_html(promise.content)}</blockquote>\n\n"
            f"قبول داری؟"
        )
        kb = receiver_confirm_keyboard(promise.id)
        try:
            await bot.send_message(chat_id=user.telegram_id, text=msg_text, reply_markup=kb)
        except Exception as e:
            logger.warning("Could not send pending notification to %s: %s", user.telegram_id, e)


# ── Reply Keyboard (persistent bottom menu) ───────────────

REPLY_MAIN_TEXTS = (
    "🤝 ثبت قول جدید",
    "📋 قول‌های من",
    "👤 پروفایل من",
    "📖 راهنما",
)


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard shown at bottom of chat."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🤝 ثبت قول جدید")
    builder.button(text="📋 قول‌های من")
    builder.row(KeyboardButton(text="👤 پروفایل من"), KeyboardButton(text="📖 راهنما"))
    return builder.as_markup(resize_keyboard=True)


def back_to_main_keyboard():
    """Inline 'back' button used inside FSM flows (edit_text target)."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 بازگشت به منوی اصلی", callback_data="main:back")
    return builder.as_markup()


async def _send_welcome(message: Message) -> None:
    """Send the welcome text with the reply keyboard."""
    await message.answer(
        "سلام! من قول‌یارم 🤝 حواسم به قول‌هایی هست که به خودت یا دوستات می‌دی، تا هیچ‌کدوم فراموش نشن.\n\nچیکار کنیم؟",
        reply_markup=get_main_reply_keyboard(),
    )


# ── /start ────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    """Handle /start with optional deep-link for promise acceptance."""
    await state.clear()

    deep_link_promise_id = None
    if command.args and command.args.startswith("promise_"):
        try:
            deep_link_promise_id = int(command.args.split("_")[1])
        except (IndexError, ValueError):
            pass

    async with get_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

        if deep_link_promise_id:
            stmt = select(Promise).where(Promise.id == deep_link_promise_id)
            res = await session.execute(stmt)
            target_promise = res.scalar_one_or_none()
            if target_promise and target_promise.status == PromiseStatus.PENDING:
                target_promise.receiver_id = user.telegram_id
                await session.commit()

                giver_stmt = select(User).where(User.telegram_id == target_promise.giver_id)
                giver_res = await session.execute(giver_stmt)
                giver = giver_res.scalar_one_or_none()
                giver_name = giver.display_name if giver else "یک کاربر"

                msg_text = (
                    f"{escape_html(giver_name)} 🫵 می‌خواد بهت یه قول بده:\n"
                    f"<blockquote>{escape_html(target_promise.content)}</blockquote>\n\n"
                    f"قبول داری؟"
                )
                kb = receiver_confirm_keyboard(target_promise.id)
                await message.answer(msg_text, reply_markup=kb)
                return

        await send_pending_notifications(message.bot, session, user)

    await _send_welcome(message)


# ── Reply Keyboard Text Handlers ─────────────────────────

@router.message(F.text == "🤝 ثبت قول جدید")
async def reply_create_promise(message: Message, state: FSMContext) -> None:
    """Handle 'ثبت قول جدید' from reply keyboard."""
    await state.clear()
    await state.set_state(PromiseStates.waiting_for_content)
    await message.answer(
        "بگو ببینم، چه قولی می‌خوای بدی؟ ✍️",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(F.text == "📋 قول‌های من")
async def reply_my_promises(message: Message) -> None:
    """Handle 'قول‌های من' from reply keyboard."""
    await message.answer(
        "قول‌های من 👇",
        reply_markup=get_my_promises_menu_keyboard(),
    )


@router.message(F.text == "👤 پروفایل من")
async def reply_profile(message: Message) -> None:
    """Handle 'پروفایل من' from reply keyboard."""
    user_id = message.from_user.id if message.from_user else 0
    text = await _build_profile_text(user_id)
    await message.answer(text, reply_markup=back_to_main_keyboard())


@router.message(F.text == "📖 راهنما")
async def reply_help(message: Message) -> None:
    """Handle 'راهنما' from reply keyboard."""
    is_group = message.chat.type in ("group", "supergroup")
    text = await _build_help_text(is_group)
    await message.answer(text, reply_markup=back_to_main_keyboard())


# ── main:back callback (inline keyboards inside flows) ────

@router.callback_query(F.data == "main:back")
async def main_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Back to main menu — edits current message to welcome text."""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "سلام! من قول‌یارم 🤝 حواسم به قول‌هایی هست که به خودت یا دوستات می‌دی، تا هیچ‌کدوم فراموش نشن.\n\nچیکار کنیم؟",
    )


# ── Back navigation in FSM flows ──────────────────────────

# State → (keyboard text, keyboard builder)
_BACK_MAP_PRIVATE = {
    PromiseStates.waiting_for_content: (
        "بگو ببینم، چه قولی می‌خوای بدی؟ ✍️",
        lambda: back_keyboard("__cancel__"),
    ),
    PromiseStates.waiting_for_confirmation: (
        None,  # will be built from data
        None,
    ),
    PromiseStates.waiting_for_deadline_choice: (
        "مهلت زمانی داره？",
        lambda: deadline_choice_keyboard_with_back(),
    ),
    PromiseStates.waiting_for_deadline_value: (
        "تاریخ رو به فرمت جلالی بنویس (مثال: ۱۴۰۵/۰۶/۱۵ یا 1405/06/15):",
        lambda: deadline_value_keyboard_with_back(),
    ),
    PromiseStates.waiting_for_target: (
        "این قول برای کیه؟",
        lambda: target_keyboard_with_back(),
    ),
    PromiseStates.waiting_for_friend_id: (
        "آیدیش رو بفرست 🔗\n"
        "بهترین راه دادن یوزرنیم یا آیدی عددیه؛ فوروارد هم کار می‌کنه ولی "
        "اگه طرف تنظیمات حریم خصوصیش محدود باشه، ممکنه نتونم بفهمم کیه.",
        lambda: friend_id_keyboard_with_back(),
    ),
}

_BACK_MAP_GROUP = {
    GroupPromiseStates.waiting_for_content: (
        None,
        None,
    ),
    GroupPromiseStates.waiting_for_confirmation: (
        None,
        None,
    ),
    GroupPromiseStates.waiting_for_deadline_choice: (
        "مهلت زمانی داره؟",
        lambda: deadline_choice_keyboard_with_back(),
    ),
    GroupPromiseStates.waiting_for_deadline_value: (
        "تاریخ رو به فرمت جلالی بنویس (مثال: ۱۴۰۵/۰۶/۱۵ یا 1405/06/15):",
        lambda: deadline_value_keyboard_with_back(),
    ),
}


async def _go_back(callback: CallbackQuery, state: FSMContext, target_state_name: str) -> None:
    """Handle back navigation in FSM flows."""
    await callback.answer()
    data = await state.get_data()
    current_state_str = await state.get_state()

    # Cancel: clear state and go to main menu
    if target_state_name == "__cancel__":
        await state.clear()
        await callback.message.edit_text(
            "سلام! من قول‌یارم 🤝 حواسم به قول‌هایی هست که به خودت یا دوستات می‌دی، تا هیچ‌کدوم فراموش نشن.\n\nچیکار کنیم؟",
        )
        return

    # Determine if private or group flow
    is_group = current_state_str and current_state_str.startswith("GroupPromiseStates")
    back_map = _BACK_MAP_GROUP if is_group else _BACK_MAP_PRIVATE

    # Find the target state object
    target_state = None
    for state_cls in [PromiseStates, GroupPromiseStates]:
        if hasattr(state_cls, target_state_name):
            target_state = getattr(state_cls, target_state_name)
            break

    if not target_state:
        await state.clear()
        await callback.message.edit_text("خطای ناوبری. از /start دوباره شروع کن.")
        return

    await state.set_state(target_state)

    # Special: back to confirmation → rebuild the confirmation message from data
    if target_state_name == "waiting_for_confirmation":
        content = data.get("content", "")
        await callback.message.edit_text(
            f"قولت: <blockquote>{escape_html(content)}</blockquote>\n\nثبت کنم؟",
            reply_markup=confirm_keyboard_with_back(),
        )
        return

    # Generic: look up text and keyboard from map
    entry = back_map.get(target_state)
    if entry and entry[0] is not None:
        text, kb_fn = entry
        kb = kb_fn() if kb_fn else None
        await callback.message.edit_text(text, reply_markup=kb)
    else:
        # Fallback: just clear
        await state.clear()
        await callback.message.edit_text("خطای ناوبری. از /start دوباره شروع کن.")


@router.callback_query(BackCallback.filter())
async def handle_back(callback: CallbackQuery, callback_data: BackCallback, state: FSMContext) -> None:
    """Route back button presses."""
    await _go_back(callback, state, callback_data.target_state)


# ── Command Handlers ─────────────────────────────────────

@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    """Handle /new — start promise creation."""
    await state.clear()
    await state.set_state(PromiseStates.waiting_for_content)
    await message.answer(
        "بگو ببینم، چه قولی می‌خوای بدی؟ ✍️",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(Command("promises"))
async def cmd_promises(message: Message) -> None:
    """Handle /promises — show my promises menu."""
    await message.answer(
        "قول‌های من 👇",
        reply_markup=get_my_promises_menu_keyboard(),
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    """Handle /profile — show user profile."""
    user_id = message.from_user.id if message.from_user else 0
    text = await _build_profile_text(user_id)
    await message.answer(text, reply_markup=back_to_main_keyboard())


# ── Help ────────────────────────────────────────────────


async def _build_help_text(is_group: bool = False) -> str:
    """Build help text for private or group chat."""
    if is_group:
        return (
            "📖 <b>راهنمای قول‌یار (گروه)</b>\n\n"
            "در گروه‌ها می‌تونی با دو روش برای کسی قول ثبت کنی:\n\n"
            "<b>۱. با تگ کردن یوزرنیم:</b>\n"
            "/promise @username\n\n"
            "<b>۲. با ریپلای به پیامش:</b>\n"
            "روی پیام شخص ریپلای کن و بفرست:\n"
            "/promise\n\n"
            "بعد از این، متن قولت رو بنویس، مهلت زمانی انتخاب کن، و تایید کن.\n"
            "شخص مورد نظر در چت خصوصی با بات، درخواست رو می‌بینه و تایید یا رد می‌کنه.\n\n"
            "<b>نکته:</b> مقصد قول (شخص مورد نظر) از تگ/ریپلای گرفته میشه، "
            "بقیه مراحل (محتوا، مهلت، تایید) مشابه فلوی خصوصیه."
        )
    else:
        return (
            "📖 <b>راهنمای قول‌یار</b>\n\n"
            "قول‌یار کمکت می‌کنه قول‌هات رو پیگیری کنی.\n\n"
            "<b>دستورات:</b>\n"
            "/start — شروع و منوی اصلی\n"
            "/new — ثبت قول جدید\n"
            "/promises — لیست قول‌های من\n"
            "/profile — پروفایل و امتیاز\n"
            "/help — نمایش این راهنما\n\n"
            "<b>قول چطور کار می‌کنه؟</b>\n"
            "1️⃣ یه قول ثبت کن (برای خودت یا دوستت)\n"
            "2️⃣ اگه برای دوسته، اون باید تایید کنه\n"
            "3️⃣ بعد از انجام، ادعای انجام بده\n"
            "4️⃣ طرف مقابل تایید یا رد می‌کنه\n"
            "5️⃣ امتیاز بگیر! 🏆"
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help — show help text."""
    is_group = message.chat.type in ("group", "supergroup")
    text = await _build_help_text(is_group)
    await message.answer(text, reply_markup=back_to_main_keyboard())


# ── Step 1: Receive promise content ──────────────────────

@router.message(PromiseStates.waiting_for_content, F.text)
async def promise_content_received(message: Message, state: FSMContext) -> None:
    """User provided promise content."""
    content = message.text.strip()
    if not content:
        await message.answer("متن قول نمی‌تونه خالی باشه. دوباره بنویس:")
        return

    await state.update_data(content=content)
    await state.set_state(PromiseStates.waiting_for_confirmation)

    await message.answer(
        f"قولت: <blockquote>{escape_html(content)}</blockquote>\n\nثبت کنم؟",
        reply_markup=confirm_keyboard_with_back(),
    )


# ── Step 2: Confirm or edit ──────────────────────────────

@router.callback_query(ConfirmPromiseCallback.filter(F.action == "yes"), PromiseStates.waiting_for_confirmation)
async def promise_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    """User confirmed the promise content."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_deadline_choice)
    await callback.message.edit_text(
        "مهلت زمانی داره؟",
        reply_markup=deadline_choice_keyboard_with_back(),
    )


@router.callback_query(ConfirmPromiseCallback.filter(F.action == "edit"), PromiseStates.waiting_for_confirmation)
async def promise_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to edit the promise content."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_content)
    await callback.message.edit_text(
        "بگو ببینم، چه قولی می‌خوای بدی؟ ✍️",
        reply_markup=back_to_main_keyboard(),
    )


# ── Step 2b: Deadline choice ─────────────────────────────

@router.callback_query(DeadlineCallback.filter(F.action.in_({"tomorrow", "week", "month", "none"})), PromiseStates.waiting_for_deadline_choice)
async def deadline_quick_choice(callback: CallbackQuery, callback_data: DeadlineCallback, state: FSMContext) -> None:
    """User chose a quick deadline option."""
    await callback.answer()

    now = datetime.now(timezone.utc)
    if callback_data.action == "tomorrow":
        deadline = now + timedelta(days=1)
        deadline = deadline.replace(hour=23, minute=59, second=0)
    elif callback_data.action == "week":
        deadline = now + timedelta(weeks=1)
        deadline = deadline.replace(hour=23, minute=59, second=0)
    elif callback_data.action == "month":
        deadline = now + timedelta(days=30)
        deadline = deadline.replace(hour=23, minute=59, second=0)
    else:  # none
        deadline = None

    await state.update_data(deadline=deadline)
    await state.set_state(PromiseStates.waiting_for_target)
    await callback.message.edit_text(
        "این قول برای کیه؟",
        reply_markup=target_keyboard_with_back(),
    )


@router.callback_query(DeadlineCallback.filter(F.action == "custom"), PromiseStates.waiting_for_deadline_choice)
async def deadline_custom(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to enter a custom Jalali date."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_deadline_value)
    await callback.message.edit_text(
        "تاریخ رو به فرمت جلالی بنویس (مثال: ۱۴۰۵/۰۶/۱۵ یا 1405/06/15):",
        reply_markup=deadline_value_keyboard_with_back(),
    )


@router.message(PromiseStates.waiting_for_deadline_value, F.text)
async def deadline_custom_value(message: Message, state: FSMContext) -> None:
    """Parse custom Jalali deadline."""
    text = message.text.strip()
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    trans_table = str.maketrans(persian_digits, english_digits)
    text = text.translate(trans_table)

    try:
        parts = text.split("/")
        if len(parts) != 3:
            raise ValueError
        jy, jm, jd = map(int, parts)

        import jdatetime
        jalali_date = jdatetime.date(jy, jm, jd)
        gregorian = jalali_date.togregorian()
        deadline = datetime(gregorian.year, gregorian.month, gregorian.day, 23, 59, 0, tzinfo=timezone.utc)

        await state.update_data(deadline=deadline)
        await state.set_state(PromiseStates.waiting_for_target)
        await message.answer(
            "این قول برای کیه؟",
            reply_markup=target_keyboard_with_back(),
        )
    except Exception:
        await message.answer("فرمت تاریخ درست نیست. مثال: ۱۴۰۵/۰۶/۱۵ یا 1405/06/15")


# ── Step 3: Choose target ────────────────────────────────

@router.callback_query(TargetCallback.filter(F.target == "self"), PromiseStates.waiting_for_target)
async def target_self(callback: CallbackQuery, state: FSMContext) -> None:
    """Promise is for the user themselves — create immediately."""
    await callback.answer()

    data = await state.get_data()
    content = data.get("content", "")
    deadline = data.get("deadline")
    user_id = callback.from_user.id if callback.from_user else 0

    async with get_session() as session:
        promise = await create_promise(
            session,
            giver_id=user_id,
            content=content,
            target_type=TargetType.SELF,
            receiver_id=user_id,
            status=PromiseStatus.CONFIRMED,
            deadline=deadline,
        )
        promise_id = promise.id

    await state.clear()
    deadline_text = ""
    if deadline:
        deadline_text = f"\n⏰ مهلت: {format_jalali_short(deadline)}"
    await callback.message.edit_text(
        f"ثبت شد ✅ قول #{promise_id} مال خودته. موفق باشی 💪{deadline_text}",
        reply_markup=back_to_main_keyboard(),
    )


@router.callback_query(TargetCallback.filter(F.target == "friend"), PromiseStates.waiting_for_target)
async def target_friend(callback: CallbackQuery, state: FSMContext) -> None:
    """Promise is for a friend — ask for their ID/username."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await callback.message.edit_text(
        "آیدیش رو بفرست 🔗\n"
        "بهترین راه دادن یوزرنیم یا آیدی عددیه؛ فوروارد هم کار می‌کنه ولی "
        "اگه طرف تنظیمات حریم خصوصیش محدود باشه، ممکنه نتونم بفهمم کیه.",
        reply_markup=friend_id_keyboard_with_back(),
    )


# ── Step 4: Receive friend identifier ────────────────────

@router.message(PromiseStates.waiting_for_friend_id, F.forward_from)
async def friend_forwarded(message: Message, state: FSMContext) -> None:
    """User forwarded a message from the friend."""
    # Try forward_from first (legacy, works when user has open privacy)
    if message.forward_from and message.forward_from.id:
        friend_id = message.forward_from.id
        await _process_friend(message, state, friend_id=friend_id)
        return
    
    # Try forward_origin (Bot API 7.0+)
    if message.forward_origin:
        from aiogram.types import MessageOriginUser, MessageOriginHiddenUser
        
        if isinstance(message.forward_origin, MessageOriginUser):
            friend_id = message.forward_origin.sender_user.id
            await _process_friend(message, state, friend_id=friend_id)
            return
        elif isinstance(message.forward_origin, MessageOriginHiddenUser):
            await message.answer(
                "⚠️ این شخص حریم خصوصیش رو طوری تنظیم کرده که نمی‌تونم از فوروارد شناساییش کنم.\n\n"
                "لطفاً یوزرنیمش رو بفرست (مثلاً @username) یا آیدی عددیش رو بده."
            )
            return
    
    await message.answer("فوروارد درست نبود. دوباره پیامش رو فوروارد کن.")


@router.message(PromiseStates.waiting_for_friend_id, F.text)
async def friend_text_identifier(message: Message, state: FSMContext) -> None:
    """User provided username or numeric ID as text."""
    if not message.text:
        return

    text = message.text.strip()

    # Check if it's a numeric ID
    if text.lstrip("-").isdigit():
        friend_id = int(text)
        await _process_friend(message, state, friend_id=friend_id)
        return

    # Username (with or without @)
    if text.startswith("@"):
        text = text[1:]
    await _process_friend(message, state, username=text)


async def _process_friend(
    message: Message,
    state: FSMContext,
    friend_id: int | None = None,
    username: str | None = None,
) -> None:
    """Process friend identifier — check if they've started the bot."""
    data = await state.get_data()
    content = data.get("content", "")
    deadline = data.get("deadline")
    user_id = message.from_user.id if message.from_user else 0

    async with get_session() as session:
        receiver: int | None = None
        friend_name = username or str(friend_id)
        can_dm = False

        if friend_id:
            user = await get_user_by_id(session, friend_id)
            if user and user.has_started_bot:
                receiver = friend_id
                friend_name = user.full_name or user.username or str(friend_id)
                can_dm = True
            else:
                receiver = friend_id
        elif username:
            user = await get_user_by_username(session, username)
            if user and user.has_started_bot:
                receiver = user.telegram_id
                friend_name = user.full_name or user.username or username
                can_dm = True
            else:
                stub = await create_stub_user(session, username)
                receiver = stub.telegram_id
                friend_name = username

        promise = await create_promise(
            session,
            giver_id=user_id,
            content=content,
            target_type=TargetType.FRIEND,
            receiver_id=receiver,
            status=PromiseStatus.PENDING,
            deadline=deadline,
        )
        promise_id = promise.id

    if can_dm:
        try:
            await message.bot.send_message(
                chat_id=receiver,
                text=(
                    f"{escape_html(message.from_user.full_name)} 🫵 می‌خواد بهت یه قول بده:\n\n"
                    f"«{escape_html(content)}»\n\n"
                    f"قبول داری؟"
                ),
                reply_markup=receiver_confirm_keyboard(promise_id),
            )
            await state.clear()
            pending_msg = await message.answer(
                "فرستادم براش، منتظر جوابشیم ⏳",
                reply_markup=back_to_main_keyboard(),
            )
            # Save message_id for edit-message flow in accept/reject
            async with get_session() as session:
                stmt = select(Promise).where(Promise.id == promise_id)
                res = await session.execute(stmt)
                p = res.scalar_one_or_none()
                if p:
                    p.giver_pending_message_id = pending_msg.message_id
                    p.giver_pending_chat_id = pending_msg.chat.id
        except Exception as e:
            logger.exception("Could not DM receiver %s (promise_id=%s): %s", receiver, promise_id, e)
            can_dm = False

    if not can_dm:
        bot_username = (await message.bot.get_me()).username
        await state.clear()
        await message.answer(
            f"هنوز {escape_html(friend_name)} با من آشنا نشده 😅\n"
            f"این لینک رو براش بفرست تا قولت بهش برسه:\n"
            f"https://t.me/{bot_username}?start=promise_{promise_id}",
            reply_markup=back_to_main_keyboard(),
        )


# ── Step 5: Receiver accepts/rejects ─────────────────────

@router.callback_query(ReceiverConfirmCallback.filter(F.action == "accept"))
async def promise_accepted(callback: CallbackQuery, callback_data: ReceiverConfirmCallback) -> None:
    """Receiver accepted the promise."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.accept_promise(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    await callback.message.edit_text(
        f"✅ قول #{promise_id} تایید شد. حالا قول‌دهنده می‌تونه ادعای انجام بده.",
    )


@router.callback_query(ReceiverConfirmCallback.filter(F.action == "reject"))
async def promise_rejected(callback: CallbackQuery, callback_data: ReceiverConfirmCallback) -> None:
    """Receiver rejected the promise — record is deleted from DB."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.reject_promise(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    await callback.message.edit_text(
        f"❌ قول #{promise_id} رد شد.",
    )


# ── Claim Done / Confirm Done / Broken / Resolve Dispute ───────────────────────

@router.callback_query(ClaimDoneCallback.filter(F.action == "claim_done"))
async def claim_done(callback: CallbackQuery, callback_data: ClaimDoneCallback) -> None:
    """Giver claims they have done the promise."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.claim_done(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
            message_id=callback.message.message_id,
            chat_id=callback.message.chat.id,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    # Edit giver's message to show waiting for confirmation
    await callback.message.edit_text(
        f"⏳ ادعای انجام قول #{promise_id} ارسال شد. در انتظار تایید طرف مقابل...",
    )


@router.callback_query(ReceiverConfirmDoneCallback.filter(F.action == "confirm_done"))
async def confirm_done(callback: CallbackQuery, callback_data: ReceiverConfirmDoneCallback) -> None:
    """Receiver confirms the promise was done."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.confirm_done(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    # Edit receiver's message
    await callback.message.edit_text(
        f"✅ قول #{promise_id} تایید شد و به عنوان انجام‌شده ثبت گردید.",
    )


@router.callback_query(ReceiverConfirmDoneCallback.filter(F.action == "dispute"))
async def dispute_done(callback: CallbackQuery, callback_data: ReceiverConfirmDoneCallback) -> None:
    """Receiver disputes the claim."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.dispute_done(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    # Edit receiver's message
    await callback.message.edit_text(
        f"⚠️ قول #{promise_id} به عنوان متنازع‌علیه (DISPUTED) علامت‌گذاری شد.",
    )


@router.callback_query(BrokenCallback.filter())
async def mark_broken(callback: CallbackQuery, callback_data: BrokenCallback) -> None:
    """Giver admits the promise is broken (no confirmation needed)."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.mark_broken(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    # Edit giver's message
    await callback.message.edit_text(
        f"💔 قول #{promise_id} ثبت نشد. خیلی بد نیس، دفعه بعد می‌ری! 💪",
    )


@router.callback_query(ResolveDisputeCallback.filter())
async def resolve_dispute(callback: CallbackQuery, callback_data: ResolveDisputeCallback) -> None:
    """Receiver changes mind and confirms after dispute."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    notifier = TelegramNotifier(callback.bot)

    async with get_session() as session:
        res = await pa.resolve_dispute(
            session, promise_id,
            actor_id=callback.from_user.id,
            notifier=notifier,
        )
        if not res.ok:
            await callback.answer(res.error, show_alert=True)
            return

    await callback.message.edit_text(
        f"✅ قول #{promise_id} تایید شد و به عنوان انجام‌شده ثبت گردید (مخالفیت حل شد).",
    )


# ── Phase 5: Promise List Grid ───────────────────────────

async def _fetch_promises(list_type: str, user_id: int) -> List[Promise]:
    """Fetch promises for the given list type and user."""
    async with get_session() as session:
        if list_type == "self":
            stmt = (
                select(Promise)
                .where(Promise.giver_id == user_id, Promise.target_type == TargetType.SELF)
                .order_by(Promise.created_at.desc())
                .options(selectinload(Promise.giver), selectinload(Promise.receiver))
            )
        elif list_type == "given":
            stmt = (
                select(Promise)
                .where(Promise.giver_id == user_id, Promise.target_type == TargetType.FRIEND)
                .order_by(Promise.created_at.desc())
                .options(selectinload(Promise.giver), selectinload(Promise.receiver))
            )
        elif list_type == "received":
            stmt = (
                select(Promise)
                .where(Promise.receiver_id == user_id, Promise.target_type == TargetType.FRIEND)
                .order_by(Promise.created_at.desc())
                .options(selectinload(Promise.giver), selectinload(Promise.receiver))
            )
        else:
            return []

        res = await session.execute(stmt)
        return list(res.scalars().all())


@router.callback_query(PromiseListCallback.filter())
async def show_promise_list(callback: CallbackQuery, callback_data: PromiseListCallback) -> None:
    """Show paginated 2x2 grid for the selected list type."""
    await callback.answer()

    if not callback.from_user:
        return

    list_type = callback_data.list_type
    page = callback_data.page
    user_id = callback.from_user.id

    if list_type not in ("self", "given", "received"):
        await callback.answer("نوع لیست نامعتبره", show_alert=True)
        return

    promises = await _fetch_promises(list_type, user_id)
    total_count = len(promises)

    if total_count == 0:
        empty_messages = {
            "self": "هنوز قولی برای خودت ثبت نکردی 🤷",
            "given": "هنوز قولی به دوستات ندادی 🤝",
            "received": "هنوز کسی بهت قول نداده 😏",
        }
        await callback.message.edit_text(
            empty_messages[list_type],
            reply_markup=get_my_promises_menu_keyboard(),
        )
        return

    header = get_promise_list_header(list_type, page, total_count)
    keyboard = get_promise_list_keyboard(promises, list_type, page, total_count)

    await callback.message.edit_text(header, reply_markup=keyboard)


@router.callback_query(PromiseItemCallback.filter())
async def show_promise_detail(callback: CallbackQuery, callback_data: PromiseItemCallback) -> None:
    """Show full promise detail when user taps a grid button."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id
    list_type = callback_data.list_type
    page = callback_data.page
    user_id = callback.from_user.id

    async with get_session() as session:
        stmt = (
            select(Promise)
            .where(Promise.id == promise_id)
            .options(selectinload(Promise.giver), selectinload(Promise.receiver))
        )
        res = await session.execute(stmt)
        promise = res.scalar_one_or_none()

    if not promise:
        await callback.answer("قول پیدا نشد!", show_alert=True)
        return

    # Check access rights
    has_access = False
    if list_type == "self" and promise.giver_id == user_id and promise.target_type == TargetType.SELF:
        has_access = True
    elif list_type == "given" and promise.giver_id == user_id and promise.target_type == TargetType.FRIEND:
        has_access = True
    elif list_type == "received" and promise.receiver_id == user_id and promise.target_type == TargetType.FRIEND:
        has_access = True

    if not has_access:
        await callback.answer("شما به این قول دسترسی ندارید", show_alert=True)
        return

    # Format the card
    card_text = format_promise_card(promise, user_id)

    # Build keyboard based on user role and promise status
    keyboard = get_promise_detail_keyboard(promise, user_id, list_type, page)

    await callback.message.edit_text(card_text, reply_markup=keyboard)


# ── Profile ──────────────────────────────────────────────

async def _build_profile_text(user_id: int) -> str:
    """Build profile text for a given user_id."""
    async with get_session() as session:
        from sqlalchemy import select, func

        total_given_stmt = select(func.count(Promise.id)).where(Promise.giver_id == user_id)
        total_given_res = await session.execute(total_given_stmt)
        total_given = total_given_res.scalar() or 0

        done_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == user_id,
            Promise.status == PromiseStatus.DONE
        )
        done_res = await session.execute(done_stmt)
        done_count = done_res.scalar() or 0

        broken_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == user_id,
            Promise.status == PromiseStatus.BROKEN
        )
        broken_res = await session.execute(broken_stmt)
        broken_count = broken_res.scalar() or 0

        total_received_stmt = select(func.count(Promise.id)).where(Promise.receiver_id == user_id)
        total_received_res = await session.execute(total_received_stmt)
        total_received = total_received_res.scalar() or 0

        accepted_stmt = select(func.count(Promise.id)).where(
            Promise.receiver_id == user_id,
            Promise.status.in_([PromiseStatus.CONFIRMED, PromiseStatus.DONE])
        )
        accepted_res = await session.execute(accepted_stmt)
        accepted_count = accepted_res.scalar() or 0

        user_stmt = select(User).where(User.telegram_id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        score = user.score if user else 0
        streak = user.current_streak if user else 0
        full_name = user.full_name if user else str(user_id)

    return (
        f"👤 پروفایل {escape_html(full_name)}\n\n"
        f"📊 امتیاز: {score}\n"
        f"🔥 استریک فعلی: {streak}\n\n"
        f"📤 قول‌های داده شده: {total_given}\n"
        f"   ✅ انجام شده: {done_count}\n"
        f"   💔 نقض شده: {broken_count}\n\n"
        f"📥 قول‌های دریافت شده: {total_received}\n"
        f"   ✅ تایید/انجام شده: {accepted_count}"
    )


# ── Group /promise command ───────────────────────────────

@router.message(Command("promise"))
async def group_promise_command(message: Message, command: CommandObject, state: FSMContext) -> None:
    """Handle /promise in groups - mention + reply to user."""
    # Clear any previous state to ensure clean start
    await state.clear()
    
    # Check if it's a group
    if message.chat.type == "private":
        await message.answer("این دستور فقط در گروه‌ها کار می‌کنه.")
        return

    # Get target user from mention or reply
    target_user = None
    if command.args:
        # Parse mention from args
        import re
        match = re.match(r"@(\w+)", command.args)
        if match:
            username = match.group(1)
            async with get_session() as session:
                target_user = await get_user_by_username(session, username)

    if not target_user and message.reply_to_message:
        reply_user_id = message.reply_to_message.from_user.id
        async with get_session() as session:
            target_user = await get_user_by_id(session, reply_user_id)

    if not target_user:
        await message.answer("کاربر پیدا نشد. یوزرنیم بده یا به پیامش ریپلای کن.")
        return

    if target_user.telegram_id == message.from_user.id:
        await message.answer("نمیتونی به خودت قول بدی از این راه! از منوی «ثبت قول جدید» استفاده کن.")
        return

    await state.set_state(GroupPromiseStates.waiting_for_content)
    await state.update_data(target_user_id=target_user.telegram_id)

    await message.answer(
        f"قول برای {target_user.display_name} ثبت می‌شه. متن قولت چیه؟ ✍️",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(GroupPromiseStates.waiting_for_content, F.text)
async def group_promise_content_received(message: Message, state: FSMContext) -> None:
    """Handle content for group promise creation."""
    content = message.text.strip()
    if not content:
        await message.answer("متن قول نمی‌تونه خالی باشه. دوباره بنویس:")
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    # Get target user for display name
    async with get_session() as session:
        target_user = await get_user_by_id(session, target_user_id)
    target_display_name = target_user.display_name if target_user else str(target_user_id)

    await state.update_data(content=content)
    await state.set_state(GroupPromiseStates.waiting_for_confirmation)

    await message.answer(
        f"قول برای {target_display_name}: <blockquote>{escape_html(content)}</blockquote>\n\nثبت کنم؟",
        reply_markup=confirm_keyboard_with_back(),
    )


@router.callback_query(ConfirmPromiseCallback.filter(F.action == "yes"), GroupPromiseStates.waiting_for_confirmation)
async def group_promise_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm group promise - move to deadline selection."""
    await callback.answer()

    await state.set_state(GroupPromiseStates.waiting_for_deadline_choice)
    await callback.message.edit_text(
        "مهلت زمانی داره؟",
        reply_markup=deadline_choice_keyboard_with_back(),
    )


@router.callback_query(DeadlineCallback.filter(F.action.in_({"tomorrow", "week", "month", "none"})), GroupPromiseStates.waiting_for_deadline_choice)
async def group_deadline_quick_choice(callback: CallbackQuery, callback_data: DeadlineCallback, state: FSMContext) -> None:
    """Group flow: quick deadline option."""
    await callback.answer()

    now = datetime.now(timezone.utc)
    if callback_data.action == "tomorrow":
        deadline = now + timedelta(days=1)
        deadline = deadline.replace(hour=23, minute=59, second=0)
    elif callback_data.action == "week":
        deadline = now + timedelta(weeks=1)
        deadline = deadline.replace(hour=23, minute=59, second=0)
    elif callback_data.action == "month":
        deadline = now + timedelta(days=30)
        deadline = deadline.replace(hour=23, minute=59, second=0)
    else:  # none
        deadline = None

    await state.update_data(deadline=deadline)

    # Target already known from /promise @user, create promise directly
    data = await state.get_data()
    content = data.get("content", "")
    target_user_id = data.get("target_user_id")
    user_id = callback.from_user.id

    if not target_user_id:
        await callback.message.edit_text("خطا: گیرنده پیدا نشد.")
        await state.clear()
        return

    async with get_session() as session:
        promise = await create_promise(
            session,
            giver_id=user_id,
            content=content,
            target_type=TargetType.FRIEND,
            receiver_id=target_user_id,
            status=PromiseStatus.PENDING,
            deadline=deadline,
        )
        promise_id = promise.id

    # Get target user for display name
    async with get_session() as session:
        target_user = await get_user_by_id(session, target_user_id)
    target_display_name = target_user.display_name if target_user else str(target_user_id)

    deadline_text = ""
    if deadline:
        deadline_text = f"\n⏰ مهلت: {format_jalali_short(deadline)}"

    await state.clear()

    # Try to DM the receiver
    try:
        await callback.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"{escape_html(callback.from_user.full_name)} 🫵 در گروه یه قول برات ثبت کرد:\n\n"
                f"«{escape_html(content)}»\n\n"
                f"قبول داری؟"
            ),
            reply_markup=receiver_confirm_keyboard(promise_id),
        )
        await callback.message.edit_text(
            f"فرستادم براش ✅ قول #{promise_id} در انتظار تایید {target_display_name}.{deadline_text}",
            reply_markup=back_to_main_keyboard(),
        )
        # Save message_id for edit-message flow in accept/reject
        async with get_session() as session:
            stmt = select(Promise).where(Promise.id == promise_id)
            res = await session.execute(stmt)
            p = res.scalar_one_or_none()
            if p:
                p.giver_pending_message_id = callback.message.message_id
                p.giver_pending_chat_id = callback.message.chat.id
    except Exception:
        bot_username = (await callback.bot.get_me()).username
        await callback.message.edit_text(
            f"هنوز این کاربر با من آشنا نشده 😅\n"
            f"این لینک رو براش بفرست: https://t.me/{bot_username}?start=promise_{promise_id}",
            reply_markup=back_to_main_keyboard(),
        )

# ── Catch-all for lost FSM state ────────────────────────────


@router.message(F.chat.type == "private")
async def catch_all_private(message: Message, state: FSMContext) -> None:
    """Catch-all for private messages that don't match any handler/state."""
    current_state = await state.get_state()
    if current_state is None:
        # User has no active FSM state - likely lost state after restart
        await message.answer(
            "🙏 به نظر می‌رسه یه‌جای کار قطع شده.\n\n"
            "لطفاً از /start دوباره شروع کن.",
            reply_markup=back_to_main_keyboard(),
        )
