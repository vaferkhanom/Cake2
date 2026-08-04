"""Handlers for promise registration flow (FSM-based) - Phase 5 complete."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command, CommandObject, CommandStart
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from src.database.models import Promise, PromiseStatus, TargetType, User
from src.database.session import (
    create_promise,
    create_stub_user,
    get_session,
    get_user_by_id,
    get_user_by_username,
    update_promise_status,
)
from src.keyboards.inline import (
    ConfirmPromiseCallback,
    ReceiverConfirmCallback,
    TargetCallback,
    PromiseStatusCallback,
    ClaimDoneCallback,
    ReceiverConfirmDoneCallback,
    DeadlineCallback,
    PromiseListCallback,
    PromiseItemCallback,
    confirm_keyboard,
    promise_status_keyboard,
    claim_done_keyboard,
    receiver_confirm_done_keyboard,
    receiver_confirm_keyboard,
    target_keyboard,
    deadline_choice_keyboard,
    get_my_promises_menu_keyboard,
    get_promise_list_keyboard,
    get_promise_list_header,
    get_promise_detail_keyboard,
    get_promise_detail_keyboard_for_receiver,
    format_promise_card,
)
from src.keyboards.reply import main_menu_keyboard
from src.states.promise import PromiseStates
from src.utils.format import (
    format_jalali_date,
    make_mention,
)


logger = logging.getLogger(__name__)
router = Router(name="promise")

# Page size for pagination
PAGE_SIZE = 4


# ── Step 1: User taps "ثبت قول جدید" ──────────────────

@router.message(F.text == "🤝 ثبت یه قول جدید")
async def new_promise_start(message: Message, state: FSMContext) -> None:
    """Start the promise creation flow — ask for promise text."""
    await state.set_state(PromiseStates.waiting_for_content)
    await message.answer("بگو ببینم، چه قولی می‌خوای بدی؟ ✍️")


# ── Step 2: User types promise content ─────────────────

@router.message(PromiseStates.waiting_for_content, F.text)
async def promise_content_received(message: Message, state: FSMContext) -> None:
    """Receive promise text and ask for confirmation."""
    if not message.text or not message.text.strip():
        await message.answer("متن قول خالیه! یه چیزی بنویس.")
        return

    content = message.text.strip()
    await state.update_data(content=content)
    await state.set_state(PromiseStates.waiting_for_confirmation)
    await message.answer(
        f"یعنی این قول ثبت بشه؟\n\n«{content}»",
        reply_markup=confirm_keyboard(),
    )


# ── Step 2b: Confirm or Edit ───────────────────────────

@router.callback_query(ConfirmPromiseCallback.filter(F.action == "yes"))
async def promise_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    """User confirmed — ask for deadline."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_deadline_choice)
    await callback.message.answer(
        "می‌خوای برای این قول مهلت بذاری؟",
        reply_markup=deadline_choice_keyboard(),
    )


@router.callback_query(ConfirmPromiseCallback.filter(F.action == "edit"))
async def promise_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to edit — go back to content step."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_content)
    await callback.message.answer("باشه، دوباره بگو 🙂")


# ── Step 3b: Deadline choice ────────────────────────────

@router.callback_query(DeadlineCallback.filter(F.action.in_(["tomorrow", "week", "month", "none"])))
async def deadline_quick_choice(callback: CallbackQuery, callback_data: DeadlineCallback, state: FSMContext) -> None:
    """User picked a quick deadline option."""
    await callback.answer()

    action = callback_data.action
    now = datetime.now(timezone.utc)
    deadline: Optional[datetime] = None

    if action == "tomorrow":
        deadline = now.replace(hour=23, minute=59, second=0, microsecond=0) + timedelta(days=1)
    elif action == "week":
        # End of this week (Friday)
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        deadline = (now + timedelta(days=days_until_friday)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "month":
        # End of this month
        if now.month == 12:
            deadline = now.replace(year=now.year + 1, month=1, day=1, hour=23, minute=59, second=0, microsecond=0) - timedelta(seconds=1)
        else:
            deadline = now.replace(month=now.month + 1, day=1, hour=23, minute=59, second=0, microsecond=0) - timedelta(seconds=1)
    elif action == "none":
        deadline = None

    await state.update_data(deadline=deadline)
    await state.set_state(PromiseStates.waiting_for_target)
    await callback.message.answer(
        "این قول برای کیه؟",
        reply_markup=target_keyboard(),
    )


@router.callback_query(DeadlineCallback.filter(F.action == "custom"))
async def deadline_custom(callback: CallbackQuery, state: FSMContext) -> None:
    """User wants to enter custom deadline (Jalali format)."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_deadline_value)
    await callback.message.answer(
        "تاریخ مهلت رو به فرمت جلالی بنویس (مثال: ۱۴۰۵/۰۶/۱۵ یا 1405/06/15):"
    )


@router.message(PromiseStates.waiting_for_deadline_value, F.text)
async def deadline_custom_value(message: Message, state: FSMContext) -> None:
    """Parse custom Jalali deadline."""
    if not message.text:
        return

    text = message.text.strip()
    # Normalize Persian digits
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
            reply_markup=target_keyboard(),
        )
    except Exception:
        await message.answer(
            "فرمت تاریخ درست نیست. مثال: ۱۴۰۵/۰۶/۱۵ یا 1405/06/15"
        )


# ── Step 3: Choose target ──────────────────────────────

@router.callback_query(TargetCallback.filter(F.target == "self"))
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
        import jdatetime
        jd = jdatetime.datetime.fromgregorian(datetime=deadline, timezone=timezone.utc)
        deadline_text = f"\n⏰ مهلت: {jd.strftime('%Y/%m/%d')}"
    await callback.message.answer(
        f"ثبت شد ✅ قول #{promise_id} مال خودته. موفق باشی 💪{deadline_text}",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(TargetCallback.filter(F.target == "friend"))
async def target_friend(callback: CallbackQuery, state: FSMContext) -> None:
    """Promise is for a friend — ask for their ID/username."""
    await callback.answer()
    await state.set_state(PromiseStates.waiting_for_friend_id)
    await callback.message.answer(
        "آیدیش رو بفرست 🔗\n"
        "اگه یوزرنیم نداره، پیامی ازش برام فوروارد کن "
        "یا آیدی عددیش رو بده."
    )


# ── Step 4: Receive friend identifier ──────────────────

@router.message(PromiseStates.waiting_for_friend_id, F.forward_from)
async def friend_forwarded(message: Message, state: FSMContext) -> None:
    """User forwarded a message from the friend."""
    if not message.forward_from or not message.forward_from.id:
        await message.answer("فوروارد درست نبود. دوباره پیامش رو فوروارد کن.")
        return

    friend_id = message.forward_from.id
    await _process_friend(message, state, friend_id=friend_id)


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

    # Check if it's a @username
    username_match = re.match(r"^@?(\w+)$", text)
    if username_match:
        username = username_match.group(1)
        await _process_friend(message, state, username=username)
        return

    await message.answer(
        "آیدی رو درست نفهمیدم. یه @یوزرنیم، آیدی عددی، یا پیام فوروارد‌شده بفرست."
    )


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
            # Check if user exists and has started bot
            user = await get_user_by_id(session, friend_id)
            if user and user.has_started_bot:
                receiver = friend_id
                friend_name = user.full_name or user.username or str(friend_id)
                can_dm = True
            else:
                # User not found or hasn't started bot
                receiver = friend_id
        elif username:
            # Check if user exists by username
            user = await get_user_by_username(session, username)
            if user and user.has_started_bot:
                receiver = user.telegram_id
                friend_name = user.full_name or user.username or username
                can_dm = True
            else:
                # Create stub user
                stub = await create_stub_user(session, username)
                receiver = stub.telegram_id
                friend_name = username

        # Create the promise
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
        # Send notification to receiver
        try:
            await message.bot.send_message(
                chat_id=receiver,
                text=(
                    f"{message.from_user.full_name} 🫵 می‌خواد بهت یه قول بده:\n"
                    f"«{content}»\n\n"
                    f"قبول داری؟"
                ),
                reply_markup=receiver_confirm_keyboard(promise_id),
            )
            await state.clear()
            await message.answer(
                "فرستادم براش، منتظر جوابشیم ⏳",
                reply_markup=main_menu_keyboard(),
            )
        except Exception as e:
            logger.warning("Could not DM receiver %s: %s", receiver, e)
            bot_username = (await message.bot.get_me()).username
            await state.clear()
            await message.answer(
                f"هنوز {friend_name} با من آشنا نشده 😅\n"
                f"این لینک رو براش بفرست تا قولت بهش برسه:\n"
                f"https://t.me/{bot_username}?start=promise_{promise_id}",
                reply_markup=main_menu_keyboard(),
            )
    else:
        # Receiver hasn't started bot
        bot_username = (await message.bot.get_me()).username
        await state.clear()
        await message.answer(
            f"هنوز {friend_name} با من آشنا نشده 😅\n"
            f"این لینک رو براش بفرست تا قولت بهش برسه:\n"
            f"https://t.me/{bot_username}?start=promise_{promise_id}",
            reply_markup=main_menu_keyboard(),
        )


# ── Step 5: Receiver accepts/rejects ───────────────────

@router.callback_query(ReceiverConfirmCallback.filter(F.action == "accept"))
async def promise_accepted(
    callback: CallbackQuery, callback_data: ReceiverConfirmCallback
) -> None:
    """Receiver accepted the promise."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id

    async with get_session() as session:
        promise = await session.get(Promise, promise_id)
        if not promise:
            await callback.answer("قول پیدا نشد!", show_alert=True)
            return

        # Verify this user is the receiver
        if promise.receiver_id != callback.from_user.id:
            await callback.answer("این دکمه برای شما نیست", show_alert=True)
            return

        promise.status = PromiseStatus.CONFIRMED
        giver_id = promise.giver_id

    receiver_mention = make_mention(callback.from_user.id, callback.from_user.full_name or callback.from_user.username or "دوست")

    await callback.message.answer(
        f"قبولش کردی ✅ حالا یادت باشه ها 😉"
    )

    # Notify the giver
    try:
        await callback.bot.send_message(
            chat_id=giver_id,
            text=f"🎉 {receiver_mention} قبول کرد! قول #{promise_id} رسماً ثبت شد.",
        )
    except Exception as e:
        logger.warning("Could not notify giver %s: %s", giver_id, e)


@router.callback_query(ReceiverConfirmCallback.filter(F.action == "reject"))
async def promise_rejected(
    callback: CallbackQuery, callback_data: ReceiverConfirmCallback
) -> None:
    """Receiver rejected the promise."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id

    async with get_session() as session:
        promise = await session.get(Promise, promise_id)
        if not promise:
            await callback.answer("قول پیدا نشد!", show_alert=True)
            return

        if promise.receiver_id != callback.from_user.id:
            await callback.answer("این دکمه برای شما نیست", show_alert=True)
            return

        promise.status = PromiseStatus.REJECTED
        giver_id = promise.giver_id

    receiver_mention = make_mention(callback.from_user.id, callback.from_user.full_name or callback.from_user.username or "دوست")

    await callback.message.answer("باشه، رد شد. مشکلی نیست 🙂")

    # Notify the giver
    try:
        await callback.bot.send_message(
            chat_id=giver_id,
            text=f"{receiver_mention} این قول رو قبول نکرد 😕 شاید بهتره باهاش حرف بزنی.",
        )
    except Exception as e:
        logger.warning("Could not notify giver %s: %s", giver_id, e)


# ── /promise group command ─────────────────────────────

@router.message(Command("promise"))
async def cmd_promise_group(message: Message, command: CommandObject) -> None:
    """Handle /promise in groups — with @mention or reply."""
    if not message.from_user:
        return

    target_user_id: int | None = None
    target_name: str | None = None
    promise_text = ""
    mention_match = None

    # Case 1: Reply to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_name = (
            message.reply_to_message.from_user.full_name
            or message.reply_to_message.from_user.username
            or str(target_user_id)
        )
        promise_text = (command.args or "").strip()

    # Case 2: @mention in text
    elif command.args:
        mention_match = re.search(r"@(\w+)", command.args)
        if mention_match:
            username = mention_match.group(1)
            async with get_session() as session:
                user = await get_user_by_username(session, username)
                if user:
                    target_user_id = user.telegram_id
                    target_name = user.full_name or user.username or username
                else:
                    target_name = f"@{username}"
            # Extract text after @mention
            promise_text = command.args[mention_match.end():].strip()

    if not target_user_id:
        await message.answer(
            "روش استفاده:\n"
            "• /promise @username قول میدم فردا بستنی بخرم\n"
            "• ریپلای روی پیام کسی + /promise قول میدم ..."
        )
        return

    if not promise_text:
        await message.answer("متن قول رو بنویس! مثلاً: /promise قول میدم فردا بستنی بخرم")
        return

    giver_id = message.from_user.id

    async with get_session() as session:
        receiver_user = await get_user_by_id(session, target_user_id)
        can_dm = receiver_user and receiver_user.has_started_bot

        promise = await create_promise(
            session,
            giver_id=giver_id,
            content=promise_text,
            target_type=TargetType.FRIEND,
            receiver_id=target_user_id,
            status=PromiseStatus.PENDING,
        )
        promise_id = promise.id

    giver_name = message.from_user.full_name or message.from_user.username or "کاربر"
    notification_text = (
        f"{make_mention(giver_id, giver_name)} 🫵 می‌خواد بهت یه قول بده:\n\n"
        f"<blockquote>{promise_text}</blockquote>\n\n"
        f"قبول داری؟"
    )

    if can_dm:
        try:
            await message.bot.send_message(
                chat_id=target_user_id,
                text=notification_text,
                reply_markup=receiver_confirm_keyboard(promise_id),
            )
        except Exception:
            can_dm = False

    if not can_dm:
        bot_username = (await message.bot.get_me()).username
        await message.answer(
            f"{target_name} 👋 یه قول برات ثبت شده، "
            f"برای دیدنش برو به @{bot_username} و /start بزن."
        )


# ── Promise status change (giver only: done/broken) ────────────────────

@router.callback_query(PromiseStatusCallback.filter(F.action == "done"))
async def mark_done(
    callback: CallbackQuery, callback_data: PromiseStatusCallback
) -> None:
    """Giver marks a promise as done."""
    await _mark_promise_status(callback, callback_data, PromiseStatus.DONE)


@router.callback_query(PromiseStatusCallback.filter(F.action == "broken"))
async def mark_broken(
    callback: CallbackQuery, callback_data: PromiseStatusCallback
) -> None:
    """Giver marks a promise as broken."""
    await _mark_promise_status(callback, callback_data, PromiseStatus.BROKEN)


async def _mark_promise_status(
    callback: CallbackQuery,
    callback_data: PromiseStatusCallback,
    new_status: PromiseStatus,
) -> None:
    """Shared logic for marking promise done/broken (giver only)."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id

    async with get_session() as session:
        promise = await session.get(Promise, promise_id)
        if not promise:
            await callback.answer("قول پیدا نشد!", show_alert=True)
            return

        if promise.giver_id != callback.from_user.id:
            await callback.answer(
                "فقط قول‌دهنده می‌تونه وضعیت رو عوض کنه", show_alert=True
            )
            return

        promise.status = new_status

    emoji = "🏆" if new_status == PromiseStatus.DONE else "💔"
    await callback.message.answer(
        f"{emoji} قول #{promise_id} با موفقیت ثبت شد."
    )


# ── Claim Done / Confirm Done flow ───────────────────────

@router.callback_query(ClaimDoneCallback.filter(F.action == "claim_done"))
async def claim_done(
    callback: CallbackQuery, callback_data: ClaimDoneCallback
) -> None:
    """Giver claims they have done the promise."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id

    async with get_session() as session:
        promise = await session.get(Promise, promise_id)
        if not promise:
            await callback.answer("قول پیدا نشد!", show_alert=True)
            return

        # Only giver can claim done
        if promise.giver_id != callback.from_user.id:
            await callback.answer(
                "فقط قول‌دهنده می‌تونه ادعای انجام بده", show_alert=True
            )
            return

        # Only CONFIRMED promises can be claimed done
        if promise.status != PromiseStatus.CONFIRMED:
            await callback.answer(
                "فقط قول‌های تایید شده قابل ادعای انجام‌ان",
                show_alert=True
            )
            return

        promise.status = PromiseStatus.CLAIMED_DONE
        promise.claimed_done_at = datetime.now(timezone.utc)

    # Notify receiver
    try:
        await callback.bot.send_message(
            chat_id=promise.receiver_id,
            text=(
                f"⚠️ {callback.from_user.full_name} می‌گه قول #{promise_id} رو انجام داده:\n\n"
                f"«{promise.content}»\n\n"
                f"تایید می‌کنی؟"
            ),
            reply_markup=receiver_confirm_done_keyboard(promise_id),
        )
    except Exception as e:
        logger.warning("Could not notify receiver %s: %s", promise.receiver_id, e)

    await callback.message.answer(
        f"⏳ ادعای انجام قول #{promise_id} ارسال شد. منتظر تایید طرف مقابلیم."
    )


@router.callback_query(ReceiverConfirmDoneCallback.filter(F.action == "confirm_done"))
async def confirm_done(
    callback: CallbackQuery, callback_data: ReceiverConfirmDoneCallback
) -> None:
    """Receiver confirms the promise was done."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id

    async with get_session() as session:
        promise = await session.get(Promise, promise_id)
        if not promise:
            await callback.answer("قول پیدا نشد!", show_alert=True)
            return

        # Only receiver can confirm
        if promise.receiver_id != callback.from_user.id:
            await callback.answer(
                "فقط گیرنده قول می‌تونه تایید کنه", show_alert=True
            )
            return

        # Must be in CLAIMED_DONE state
        if promise.status != PromiseStatus.CLAIMED_DONE:
            await callback.answer(
                "این قول در وضعیت قابل تایید نیست",
                show_alert=True
            )
            return

        promise.status = PromiseStatus.DONE
        promise.resolved_at = datetime.now(timezone.utc)

        # Update giver's score and streak
        from src.services.scoring import apply_done_score
        await apply_done_score(session, promise.giver_id)

    await callback.message.answer(
        f"✅ قول #{promise_id} تایید شد و به عنوان انجام‌شده ثبت گردید."
    )

    # Notify giver
    try:
        await callback.bot.send_message(
            chat_id=promise.giver_id,
            text=f"🎉 {callback.from_user.full_name} تایید کرد که قول #{promise_id} انجام شده!",
        )
    except Exception as e:
        logger.warning("Could not notify giver %s: %s", promise.giver_id, e)


@router.callback_query(ReceiverConfirmDoneCallback.filter(F.action == "dispute"))
async def dispute_done(
    callback: CallbackQuery, callback_data: ReceiverConfirmDoneCallback
) -> None:
    """Receiver disputes the claim."""
    await callback.answer()

    if not callback.from_user:
        return

    promise_id = callback_data.promise_id

    async with get_session() as session:
        promise = await session.get(Promise, promise_id)
        if not promise:
            await callback.answer("قول پیدا نشد!", show_alert=True)
            return

        if promise.receiver_id != callback.from_user.id:
            await callback.answer(
                "فقط گیرنده قول می‌تونه رد کنه", show_alert=True
            )
            return

        if promise.status != PromiseStatus.CLAIMED_DONE:
            await callback.answer(
                "این قول در وضعیت قابل رد نیست",
                show_alert=True
            )
            return

        promise.status = PromiseStatus.DISPUTED

    await callback.message.answer(
        f"⚠️ قول #{promise_id} به عنوان متنازع‌علیه (DISPUTED) علامت‌گذاری شد."
    )

    # Notify giver
    try:
        await callback.bot.send_message(
            chat_id=promise.giver_id,
            text=(
                f"⚠️ {callback.from_user.full_name} ادعای انجام قول #{promise_id} رو رد کرد.\n"
                f"وضعیت: DISPUTED\n"
                f"می‌تونی با طرف مقابل صحبت کنی و دوباره ادعا کنی."
            ),
        )
    except Exception as e:
        logger.warning("Could not notify giver %s: %s", promise.giver_id, e)


# ── Phase 5: Promise List Grid ───────────────────────────

async def _fetch_promises(list_type: str, user_id: int) -> List[Promise]:
    """Fetch promises for the given list type and user."""
    async with get_session() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

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


@router.message(F.text == "📋 قول‌های من")
async def show_my_promises_menu(message: Message) -> None:
    """Show the main 'My Promises' menu with 3 options."""
    await message.answer(
        "قول‌های من 👇",
        reply_markup=get_my_promises_menu_keyboard(),
    )


@router.callback_query(PromiseListCallback.filter())
async def show_promise_list(callback: CallbackQuery, callback_data: PromiseListCallback) -> None:
    """Show paginated 2x2 grid for the selected list type."""
    await callback.answer()

    if not callback.from_user:
        return

    list_type = callback_data.list_type
    page = callback_data.page
    user_id = callback.from_user.id

    # Validate list_type
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
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

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
    is_giver = False
    if list_type == "self" and promise.giver_id == user_id and promise.target_type == TargetType.SELF:
        has_access = True
        is_giver = True
    elif list_type == "given" and promise.giver_id == user_id and promise.target_type == TargetType.FRIEND:
        has_access = True
        is_giver = True
    elif list_type == "received" and promise.receiver_id == user_id and promise.target_type == TargetType.FRIEND:
        has_access = True
        is_giver = False

    if not has_access:
        await callback.answer("شما به این قول دسترسی ندارید", show_alert=True)
        return

    # Format the card
    card_text = format_promise_card(promise, user_id)

    # Build keyboard based on user role and promise status
    if is_giver:
        keyboard = get_promise_detail_keyboard(
            promise_id=promise.id,
            giver_id=promise.giver_id,
            list_type=list_type,
            page=page,
        )
    else:
        keyboard = get_promise_detail_keyboard_for_receiver(
            promise_id=promise.id,
            list_type=list_type,
            page=page,
        )

    await callback.message.edit_text(card_text, reply_markup=keyboard)


# Back to list is handled by PromiseListCallback (already implemented above)


# ── Profile ──────────────────────────────────────────────

@router.message(F.text == "👤 پروفایل من")
async def show_profile(message: Message) -> None:
    """Show user profile with credibility score."""
    async with get_session() as session:
        from sqlalchemy import select, func

        total_given_stmt = select(func.count(Promise.id)).where(Promise.giver_id == message.from_user.id)
        total_given_res = await session.execute(total_given_stmt)
        total_given = total_given_res.scalar() or 0

        done_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == message.from_user.id,
            Promise.status == PromiseStatus.DONE
        )
        done_res = await session.execute(done_stmt)
        done_count = done_res.scalar() or 0

        broken_stmt = select(func.count(Promise.id)).where(
            Promise.giver_id == message.from_user.id,
            Promise.status == PromiseStatus.BROKEN
        )
        broken_res = await session.execute(broken_stmt)
        broken_count = broken_res.scalar() or 0

        total_received_stmt = select(func.count(Promise.id)).where(Promise.receiver_id == message.from_user.id)
        total_received_res = await session.execute(total_received_stmt)
        total_received = total_received_res.scalar() or 0

        denominator = done_count + broken_count
        if denominator == 0:
            credibility_text = "هنوز قولی رو به سرانجام نرسوندی"
        else:
            pct = round((done_count / denominator) * 100)
            credibility_text = f"{pct}%\n({done_count} از {denominator} قول رو انجام دادی)"

        await message.answer(
            f"👤 پروفایل تو\n\n📊 اعتبار: {credibility_text}\n\n🤝 کل قول‌های دادی: {total_given}\n📥 کل قول‌های گرفتی: {total_received}"
        )


# ── Start command ────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command with deep link support."""
    await state.clear()

    args = message.text.split(maxsplit=1) if message.text else []
    deep_link_promise_id = None
    if len(args) > 1 and args[1].startswith("promise_"):
        try:
            deep_link_promise_id = int(args[1].replace("promise_", ""))
        except ValueError:
            pass

    async with get_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

        if deep_link_promise_id:
            stmt = select(Promise).where(Promise.promise_id == deep_link_promise_id)
            res = await session.execute(stmt)
            target_promise = res.scalar_one_or_none()
            if target_promise and target_promise.status == PromiseStatus.PENDING:
                target_promise.receiver_id = user.telegram_id
                await session.commit()

                giver_stmt = select(User).where(User.telegram_id == target_promise.giver_id)
                giver_res = await session.execute(giver_stmt)
                giver = giver_res.scalar_one_or_none()
                giver_name = giver.display_name if giver else "یک کاربر"

                msg_text = f"{giver_name} 🫵 می‌خواد بهت یه قول بده:\n«{target_promise.content}»\nقبول داری؟"
                kb = receiver_confirm_keyboard(target_promise.promise_id or target_promise.id)
                await message.answer(msg_text, reply_markup=kb)
                return

        # Send pending notifications for this user
        await send_pending_notifications(message.bot, session, user)

    await message.answer(
        "سلام! من قول‌یارم 🤝 حواسم به قول‌هایی هست که به خودت یا دوستات می‌دی، تا هیچ‌کدوم فراموش نشن.\n\nچیکار کنیم؟",
        reply_markup=main_menu_keyboard(),
    )


async def send_pending_notifications(bot, session, user: User) -> None:
    """Send pending promise notifications to user on startup."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Promise)
        .where(Promise.receiver_id == user.telegram_id, Promise.status == PromiseStatus.PENDING)
        .options(selectinload(Promise.giver))
    )
    res = await session.execute(stmt)
    promises = res.scalars().all()

    for promise in promises:
        giver_name = promise.giver.display_name if promise.giver else "یک کاربر"
        msg_text = f"{giver_name} 🫵 می‌خواد بهت یه قول بده:\n«{promise.content}»\nقبول داری؟"
        kb = receiver_confirm_keyboard(promise.promise_id or promise.id)
        try:
            await bot.send_message(user.telegram_id, msg_text, reply_markup=kb)
        except Exception:
            pass


async def get_or_create_user(session, telegram_id: int, username: str | None, full_name: str) -> User:
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
                select(Promise).where(Promise.receiver_id == old_id)
            )
            from sqlalchemy import update
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