from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Promise, TargetType, PromiseStatus
from src.database.session import AsyncSessionLocal
from src.keyboards.inline import (
    get_main_reply_keyboard,
    get_confirm_keyboard,
    get_target_keyboard,
    get_receiver_approval_keyboard,
    get_list_promises_keyboard,
    get_promise_detail_keyboard,
)
from src.states.promise import PromiseForm
from src.config import settings

router = Router()

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str) -> User:
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

async def send_pending_notifications(bot, session: AsyncSession, user: User):
    stmt = select(Promise).where(
        Promise.receiver_id == user.telegram_id,
        Promise.status == PromiseStatus.PENDING
    )
    res = await session.execute(stmt)
    promises = res.scalars().all()
    
    for promise in promises:
        giver_stmt = select(User).where(User.telegram_id == promise.giver_id)
        giver_res = await session.execute(giver_stmt)
        giver = giver_res.scalar_one_or_none()
        giver_name = giver.display_name if giver else "یک کاربر"
        
        msg_text = f"{giver_name} 🫵 می‌خواد بهت یه قول بده:\n«{promise.content}»\nقبول داری؟"
        kb = get_receiver_approval_keyboard(promise.promise_id or promise.id, user.telegram_id)
        try:
            await bot.send_message(user.telegram_id, msg_text, reply_markup=kb)
        except Exception:
            pass

async def get_next_promise_id(session: AsyncSession) -> int:
    """Get next sequential promise_id"""
    stmt = select(func.max(Promise.promise_id))
    res = await session.execute(stmt)
    max_id = res.scalar()
    return (max_id or 0) + 1

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    args = message.text.split(maxsplit=1)
    deep_link_promise_id = None
    if len(args) > 1 and args[1].startswith("promise_"):
        try:
            deep_link_promise_id = int(args[1].replace("promise_", ""))
        except ValueError:
            pass

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        
        if deep_link_promise_id:
            p_stmt = select(Promise).where(Promise.promise_id == deep_link_promise_id)
            p_res = await session.execute(p_stmt)
            target_promise = p_res.scalar_one_or_none()
            if target_promise and target_promise.status == PromiseStatus.PENDING:
                target_promise.receiver_id = user.telegram_id
                await session.commit()
                
                giver_stmt = select(User).where(User.telegram_id == target_promise.giver_id)
                giver_res = await session.execute(giver_stmt)
                giver = giver_res.scalar_one_or_none()
                giver_name = giver.display_name if giver else "یک کاربر"

                msg_text = f"{giver_name} 🫵 می‌خواد بهت یه قول بده:\n«{target_promise.content}»\nقبول داری؟"
                kb = get_receiver_approval_keyboard(target_promise.promise_id or target_promise.id, user.telegram_id)
                await message.answer(msg_text, reply_markup=kb)
                return

        await send_pending_notifications(message.bot, session, user)

    await message.answer(
        "سلام! من قول‌یارم 🤝 حواسم به قول‌هایی هست که به خودت یا دوستات می‌دی، تا هیچ‌کدوم فراموش نشن.\n\nچیکار کنیم؟",
        reply_markup=get_main_reply_keyboard(),
    )

@router.message(F.text == settings.MENU_OPTIONS["CREATE_PROMISE"])
async def start_create_promise(message: Message, state: FSMContext):
    await state.set_state(PromiseForm.waiting_for_content)
    await message.answer("بگو ببینم، چه قولی می‌خوای بدی؟ ✍️")

@router.message(PromiseForm.waiting_for_content, F.text)
async def process_promise_content(message: Message, state: FSMContext):
    await state.update_data(content=message.text)
    await state.set_state(PromiseForm.waiting_for_initial_confirm)
    await message.answer(
        f"یعنی این قول ثبت بشه؟\n\n«{message.text}»",
        reply_markup=get_confirm_keyboard(message.from_user.id)
    )

@router.callback_query(PromiseForm.waiting_for_initial_confirm, F.data.startswith("confirm_initial:"))
async def process_initial_confirm(callback: CallbackQuery, state: FSMContext):
    _, action, user_id_str = callback.data.split(":")
    if int(user_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return

    if action == "no":
        await state.set_state(PromiseForm.waiting_for_content)
        await callback.message.edit_text("باشه، دوباره بگو 🙂")
        return

    await state.set_state(PromiseForm.waiting_for_target)
    await callback.message.edit_text(
        "این قول برای کیه؟",
        reply_markup=get_target_keyboard(callback.from_user.id)
    )

@router.callback_query(PromiseForm.waiting_for_target, F.data.startswith("target:"))
async def process_target_selection(callback: CallbackQuery, state: FSMContext):
    _, target, user_id_str = callback.data.split(":")
    if int(user_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return

    data = await state.get_data()
    content = data.get("content")

    if target == "self":
        async with AsyncSessionLocal() as session:
            giver = await get_or_create_user(
                session,
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                full_name=callback.from_user.full_name,
            )
            promise_id = await get_next_promise_id(session)
            promise = Promise(
                promise_id=promise_id,
                content=content,
                giver_id=giver.telegram_id,
                receiver_id=None,
                target_type=TargetType.SELF,
                status=PromiseStatus.CONFIRMED,
            )
            session.add(promise)
            await session.commit()

        await state.clear()
        await callback.message.edit_text(f"ثبت شد ✅ قول #{promise_id} مال خودته. موفق باشی 💪")
        return

    await state.set_state(PromiseForm.waiting_for_receiver_id)
    await callback.message.edit_text(
        "آیدیش رو بفرست 🔗\nاگه یوزرنیم نداره، پیامی ازش برام فوروارد کن یا آیدی عددیش رو بده."
    )

@router.message(PromiseForm.waiting_for_receiver_id)
async def process_receiver_id(message: Message, state: FSMContext):
    data = await state.get_data()
    content = data.get("content")

    receiver_user_id = None
    receiver_username = None

    if message.forward_from:
        receiver_user_id = message.forward_from.id
        receiver_username = message.forward_from.username
    elif message.forward_sender_name:
        await message.answer("تنظیمات حریم خصوصی این کاربر اجازه دریافت آیدی رو نمیده. لطفاً یوزرنیم یا آیدی عددی رو وارد کنید.")
        return
    elif message.text:
        text = message.text.strip()
        if text.startswith("@"):
            receiver_username = text.lstrip("@")
        elif text.isdigit():
            receiver_user_id = int(text)
        else:
            receiver_username = text

    if not receiver_user_id and not receiver_username:
        await message.answer("لطفاً یک آیدی معتبر، یوزرنیم و یا پیام فوروارد شده ارسال کنید.")
        return

    async with AsyncSessionLocal() as session:
        giver = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

        receiver = None
        if receiver_user_id:
            stmt = select(User).where(User.telegram_id == receiver_user_id)
            res = await session.execute(stmt)
            receiver = res.scalar_one_or_none()
        elif receiver_username:
            stmt = select(User).where(User.username == receiver_username)
            res = await session.execute(stmt)
            receiver = res.scalar_one_or_none()

        if not receiver:
            receiver = User(
                telegram_id=receiver_user_id if receiver_user_id else 0,
                username=receiver_username,
                full_name=receiver_username or str(receiver_user_id or "دوست"),
                has_started_bot=False,
            )
            if not receiver_user_id:
                import random
                receiver.telegram_id = -random.randint(1000000, 9999999)
            session.add(receiver)
            await session.commit()

        promise_id = await get_next_promise_id(session)
        promise = Promise(
            promise_id=promise_id,
            content=content,
            giver_id=giver.telegram_id,
            receiver_id=receiver.telegram_id,
            target_type=TargetType.FRIEND,
            status=PromiseStatus.PENDING,
        )
        session.add(promise)
        await session.commit()
        await session.refresh(promise)

        await state.clear()
        await message.answer("فرستادم براش، منتظر جوابشیم ⏳")

        bot_info = await message.bot.get_me()
        bot_username = bot_info.username

        friend_display = receiver.display_name

        if receiver.has_started_bot and receiver.telegram_id > 0:
            msg_text = f"{giver.display_name} 🫵 می‌خواد بهت یه قول بده:\n«{content}»\nقبول داری؟"
            kb = get_receiver_approval_keyboard(promise.promise_id, receiver.telegram_id)
            try:
                await message.bot.send_message(receiver.telegram_id, msg_text, reply_markup=kb)
            except Exception:
                pass
        else:
            invite_link = f"https://t.me/{bot_username}?start=promise_{promise.promise_id}"
            await message.answer(
                f"هنوز {friend_display} با من آشنا نشده 😅 این لینک رو براش بفرست تا قولت بهش برسه:\n{invite_link}"
            )

@router.callback_query(F.data.startswith("promise_appr:"))
async def process_promise_approval(callback: CallbackQuery):
    _, action, promise_id_str, receiver_id_str = callback.data.split(":")
    if int(receiver_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return

    promise_id = int(promise_id_str)
    async with AsyncSessionLocal() as session:
        stmt = select(Promise).where(Promise.promise_id == promise_id)
        res = await session.execute(stmt)
        promise = res.scalar_one_or_none()

        if not promise or promise.status != PromiseStatus.PENDING:
            await callback.answer("این قول معتبر نیست یا قبلاً بررسی شده.", show_alert=True)
            return

        receiver_stmt = select(User).where(User.telegram_id == callback.from_user.id)
        receiver_res = await session.execute(receiver_stmt)
        receiver = receiver_res.scalar_one_or_none()
        receiver_name = receiver.display_name if receiver else callback.from_user.full_name

        giver_stmt = select(User).where(User.telegram_id == promise.giver_id)
        giver_res = await session.execute(giver_stmt)
        giver = giver_res.scalar_one_or_none()
        giver_name = giver.display_name if giver else "دوست"

        if action == "yes":
            promise.status = PromiseStatus.CONFIRMED
            await session.commit()

            await callback.message.edit_text("قبولش کردی ✅ حالا یادت باشه ها 😉")
            
            giver_msg = f"🎉 {receiver_name} قبول کرد! قول #{promise_id} رسماً ثبت شد."
            try:
                await callback.bot.send_message(promise.giver_id, giver_msg)
            except Exception: pass

        elif action == "no":
            promise.status = PromiseStatus.REJECTED
            await session.commit()

            await callback.message.edit_text("باشه، رد شد. مشکلی نیست 🙂")

            giver_msg = f"{receiver_name} این قول رو قبول نکرد 😕 شاید بهتره باهاش حرف بزنی."
            try:
                await callback.bot.send_message(promise.giver_id, giver_msg)
            except Exception: pass

@router.message(F.text == settings.MENU_OPTIONS["LIST_PROMISES"])
async def start_list_promises(message: Message):
    await message.answer(
        "کدوم لیست؟",
        reply_markup=get_list_promises_keyboard(message.from_user.id)
    )

@router.callback_query(F.data.startswith("list_promises:"))
async def process_list_promises(callback: CallbackQuery):
    _, list_type, user_id_str = callback.data.split(":")
    if int(user_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        if list_type == "my":
            stmt = select(Promise).where(
                Promise.giver_id == callback.from_user.id
            ).order_by(Promise.created_at.desc())
            res = await session.execute(stmt)
            promises = res.scalars().all()

            if not promises:
                await callback.message.edit_text("هنوز قولی ندادی 🤷 وقتشه یکی بدی!")
                return

            items = []
            for p in promises:
                target_str = "خودم"
                if p.receiver_id:
                    rec_stmt = select(User).where(User.telegram_id == p.receiver_id)
                    rec_res = await session.execute(rec_stmt)
                    rec = rec_res.scalar_one_or_none()
                    if rec: target_str = rec.display_name
                
                item = f"#{p.promise_id} · {p.status_display}\n💬 {p.content}\n👤 به: {target_str}\n🗓 {p.jalali_created_at}"
                items.append(item)

            await callback.message.edit_text("\n\n".join(items))

        elif list_type == "friends":
            stmt = select(Promise).where(
                Promise.receiver_id == callback.from_user.id
            ).order_by(Promise.created_at.desc())
            res = await session.execute(stmt)
            promises = res.scalars().all()

            if not promises:
                await callback.message.edit_text("هنوز کسی بهت قول نداده... 😏")
                return

            items = []
            for p in promises:
                giver_stmt = select(User).where(User.telegram_id == p.giver_id)
                giver_res = await session.execute(giver_stmt)
                giver = giver_res.scalar_one_or_none()
                giver_str = giver.display_name if giver else "دوست"

                item = f"#{p.promise_id} · {p.status_display}\n💬 {p.content}\n👤 از: {giver_str}\n🗓 {p.jalali_created_at}"
                items.append(item)

            await callback.message.edit_text("\n\n".join(items))

@router.callback_query(F.data.startswith("promise_status:"))
async def process_promise_status_change(callback: CallbackQuery):
    _, action, promise_id_str, giver_id_str = callback.data.split(":")
    if int(giver_id_str) != callback.from_user.id:
        await callback.answer("فقط قول‌دهنده می‌تونه وضعیت رو عوض کنه", show_alert=True)
        return

    promise_id = int(promise_id_str)
    async with AsyncSessionLocal() as session:
        stmt = select(Promise).where(Promise.promise_id == promise_id).options(selectinload(Promise.receiver))
        res = await session.execute(stmt)
        promise = res.scalar_one_or_none()

        if not promise or promise.status != PromiseStatus.CONFIRMED:
            await callback.answer("فقط قول‌های تاییدشده می‌تونن به انجام/نقض تغییر کنن", show_alert=True)
            return

        receiver_display = promise.receiver.display_name if promise.receiver else "دوست"

        if action == "done":
            promise.status = PromiseStatus.DONE
            await session.commit()
            await callback.message.edit_text(
                f"#{promise.promise_id} · {promise.status_display}\n💬 {promise.content}\n👤 به: {receiver_display}\n🗓 {promise.jalali_created_at}",
                reply_markup=get_promise_detail_keyboard(promise.promise_id, promise.giver_id)
            )
        elif action == "broken":
            promise.status = PromiseStatus.BROKEN
            await session.commit()
            await callback.message.edit_text(
                f"#{promise.promise_id} · {promise.status_display}\n💬 {promise.content}\n👤 به: {receiver_display}\n🗓 {promise.jalali_created_at}",
                reply_markup=get_promise_detail_keyboard(promise.promise_id, promise.giver_id)
            )

@router.message(F.text == settings.MENU_OPTIONS["PROFILE"])
async def show_profile(message: Message):
    async with AsyncSessionLocal() as session:
        # Count promises by status for this user as giver
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

@router.message(Command("promise"))
async def group_promise_command(message: Message, state: FSMContext):
    """Handle /promise @username text or reply /promise text"""
    if message.chat.type == "private":
        await message.answer("این دستور فقط در گروه‌ها کار می‌کنه. برای ثبت قول در چت خصوصی از منو استفاده کن.")
        return

    # Extract receiver and content
    receiver_user_id = None
    receiver_username = None
    content = None

    # Case 1: Reply to a message
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        if replied_user.is_bot:
            await message.answer("نمیتونی به ربات قول بدی 😅")
            return
        receiver_user_id = replied_user.id
        receiver_username = replied_user.username
        # Get content after command
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            content = parts[1]
        else:
            await message.answer("متن قول رو هم بنویس بعد از دستور.")
            return
    
    # Case 2: Mention @username
    else:
        parts = message.text.split(maxsplit=2)
        if len(parts) >= 3 and parts[1].startswith("@"):
            receiver_username = parts[1].lstrip("@")
            content = parts[2]
        else:
            await message.answer(
                "فرمت درست:\n"
                "• ریپلای روی پیام دوست + `/promise متن قول`\n"
                "• یا `/promise @username متن قول`"
            )
            return

    if not content:
        await message.answer("متن قول رو بنویس.")
        return

    # Now we have content and either receiver_user_id or receiver_username
    # Resolve receiver
    async with AsyncSessionLocal() as session:
        giver = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

        receiver = None
        if receiver_user_id:
            stmt = select(User).where(User.telegram_id == receiver_user_id)
            res = await session.execute(stmt)
            receiver = res.scalar_one_or_none()
        elif receiver_username:
            stmt = select(User).where(User.username == receiver_username)
            res = await session.execute(stmt)
            receiver = res.scalar_one_or_none()

        if not receiver:
            receiver = User(
                telegram_id=receiver_user_id if receiver_user_id else 0,
                username=receiver_username,
                full_name=receiver_username or str(receiver_user_id or "دوست"),
                has_started_bot=False,
            )
            if not receiver_user_id:
                import random
                receiver.telegram_id = -random.randint(1000000, 9999999)
            session.add(receiver)
            await session.commit()

        promise_id = await get_next_promise_id(session)
        promise = Promise(
            promise_id=promise_id,
            content=content,
            giver_id=giver.telegram_id,
            receiver_id=receiver.telegram_id,
            target_type=TargetType.FRIEND,
            status=PromiseStatus.PENDING,
        )
        session.add(promise)
        await session.commit()

        friend_display = receiver.display_name

        # Try to DM receiver
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username

        if receiver.has_started_bot and receiver.telegram_id > 0:
            msg_text = f"{giver.display_name} 🫵 می‌خواد بهت یه قول بده:\n«{content}»\nقبول داری؟"
            kb = get_receiver_approval_keyboard(promise.promise_id, receiver.telegram_id)
            try:
                await message.bot.send_message(receiver.telegram_id, msg_text, reply_markup=kb)
                await message.answer("فرستادم براش در پیوی، منتظر جوابشیم ⏳")
            except Exception:
                # Can't DM, notify in group
                await message.reply(f"{friend_display} 👋 یه قول برات ثبت شده، برای دیدنش برو به @{bot_username} و /start بزن.")
        else:
            invite_link = f"https://t.me/{bot_username}?start=promise_{promise.promise_id}"
            await message.reply(
                f"هنوز {friend_display} با من آشنا نشده 😅 این لینک رو براش بفرست تا قولت بهش برسه:\n{invite_link}"
            )