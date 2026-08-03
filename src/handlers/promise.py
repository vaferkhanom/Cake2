from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Promise, TargetType, PromiseStatus
from src.database.session import AsyncSessionLocal
from src.keyboards.inline import (
    get_main_reply_keyboard,
    get_confirm_keyboard,
    get_target_keyboard,
    get_receiver_approval_keyboard,
    get_list_promises_keyboard,
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
            # Safely update foreign key references in promises pointing to the stub negative ID
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
        
        msg_text = f"{giver_name} میخواد به شما یک قول بده\n{promise.content}"
        kb = get_receiver_approval_keyboard(promise.id, user.telegram_id)
        try:
            await bot.send_message(user.telegram_id, msg_text, reply_markup=kb)
        except Exception:
            pass

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
            p_stmt = select(Promise).where(Promise.id == deep_link_promise_id)
            p_res = await session.execute(p_stmt)
            target_promise = p_res.scalar_one_or_none()
            if target_promise and target_promise.status == PromiseStatus.PENDING:
                target_promise.receiver_id = user.telegram_id
                await session.commit()
                
                giver_stmt = select(User).where(User.telegram_id == target_promise.giver_id)
                giver_res = await session.execute(giver_stmt)
                giver = giver_res.scalar_one_or_none()
                giver_name = giver.display_name if giver else "یک کاربر"

                msg_text = f"{giver_name} میخواد به شما یک قول بده\n{target_promise.content}"
                kb = get_receiver_approval_keyboard(target_promise.id, user.telegram_id)
                await message.answer(msg_text, reply_markup=kb)
                return

        await send_pending_notifications(message.bot, session, user)

    await message.answer(
        "سلام خوش اومدی، میتونی با کمک من قول هاتو با دوستات ثبت کنی، چه کاری میخوای برات انجام بدم؟",
        reply_markup=get_main_reply_keyboard(),
    )

@router.message(F.text == settings.MENU_OPTIONS["CREATE_PROMISE"])
async def start_create_promise(message: Message, state: FSMContext):
    await state.set_state(PromiseForm.waiting_for_content)
    await message.answer("حتما! چه قولی میخوای بدی؟")

@router.message(PromiseForm.waiting_for_content, F.text)
async def process_promise_content(message: Message, state: FSMContext):
    await state.update_data(content=message.text)
    await state.set_state(PromiseForm.waiting_for_initial_confirm)
    await message.answer(
        "مطمئنی؟",
        reply_markup=get_confirm_keyboard(message.from_user.id)
    )

@router.callback_query(PromiseForm.waiting_for_initial_confirm, F.data.startswith("confirm_initial:"))
async def process_initial_confirm(callback: CallbackQuery, state: FSMContext):
    _, action, user_id_str = callback.data.split(":")
    if int(user_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return

    if action == "no":
        await state.clear()
        await callback.message.edit_text("عملیات لغو شد.")
        await callback.message.answer(
            "چه کاری میخوای برات انجام بدم؟",
            reply_markup=get_main_reply_keyboard()
        )
        return

    await state.set_state(PromiseForm.waiting_for_target)
    await callback.message.edit_text(
        "میخوای به چه کسی قول بدی؟",
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
            promise = Promise(
                content=content,
                giver_id=giver.telegram_id,
                receiver_id=None,
                target_type=TargetType.SELF,
                status=PromiseStatus.CONFIRMED,
            )
            session.add(promise)
            await session.commit()

        await state.clear()
        await callback.message.edit_text("قول شما ثبت شد")
        return

    await state.set_state(PromiseForm.waiting_for_receiver_id)
    await callback.message.edit_text(
        "آیدی دوست خود را وارد کنید، (توجه: اگر دوست شما آیدی نداره، یک پیام فوروارد کنید و یا آیدی عددی اون رو وارد کنید)"
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

        promise = Promise(
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
        await message.answer("در انتظار تایید قول...")

        bot_info = await message.bot.get_me()
        bot_username = bot_info.username

        if receiver.has_started_bot and receiver.telegram_id > 0:
            msg_text = f"{giver.display_name} میخواد به شما یک قول بده\n{content}"
            kb = get_receiver_approval_keyboard(promise.id, receiver.telegram_id)
            try:
                await message.bot.send_message(receiver.telegram_id, msg_text, reply_markup=kb)
            except Exception:
                pass
        else:
            invite_link = f"https://t.me/{bot_username}?start=promise_{promise.id}"
            await message.answer(
                f"دوست شما هنوز ربات رو استارت نکرده. لینک زیر رو براتون فرستادیم تا برای دوستتون ارسال کنید تا قول رو ببینه و تایید کنه:\n{invite_link}"
            )

@router.callback_query(F.data.startswith("promise_appr:"))
async def process_promise_approval(callback: CallbackQuery):
    _, action, promise_id_str, receiver_id_str = callback.data.split(":")
    if int(receiver_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return

    promise_id = int(promise_id_str)
    async with AsyncSessionLocal() as session:
        stmt = select(Promise).where(Promise.id == promise_id)
        res = await session.execute(stmt)
        promise = res.scalar_one_or_none()

        if not promise or promise.status != PromiseStatus.PENDING:
            await callback.answer("این قول معتبر نیست یا قبلاً بررسی شده.", show_alert=True)
            return

        receiver_stmt = select(User).where(User.telegram_id == callback.from_user.id)
        receiver_res = await session.execute(receiver_stmt)
        receiver = receiver_res.scalar_one_or_none()
        receiver_name = receiver.display_name if receiver else callback.from_user.full_name

        if action == "yes":
            promise.status = PromiseStatus.CONFIRMED
            await session.commit()
            await callback.message.edit_text("تایید شد")
            try:
                await callback.bot.send_message(promise.giver_id, f"قول شما تایید شد، قول با محتوای {promise.content} به شخص {receiver_name} ثبت شد.")
            except Exception: pass
        elif action == "no":
            promise.status = PromiseStatus.REJECTED
            await session.commit()
            await callback.message.edit_text("قول رو رد کردی.")
            try:
                await callback.bot.send_message(promise.giver_id, f"متاسفانه {receiver_name} قول شما رو رد کرد.")
            except Exception: pass

@router.message(F.text == settings.MENU_OPTIONS["LIST_PROMISES"])
async def start_list_promises(message: Message):
    await message.answer("لیست قول هات رو انتخاب کن", reply_markup=get_list_promises_keyboard(message.from_user.id))

@router.callback_query(F.data.startswith("list_promises:"))
async def process_list_promises(callback: CallbackQuery):
    _, list_type, user_id_str = callback.data.split(":")
    if int(user_id_str) != callback.from_user.id:
        await callback.answer("این دکمه برای شما نیست", show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        if list_type == "my":
            stmt = select(Promise).where(Promise.giver_id == callback.from_user.id, Promise.status == PromiseStatus.CONFIRMED)
            res = await session.execute(stmt)
            promises = res.scalars().all()
            if not promises:
                await callback.message.edit_text("هیچ قولی توسط شما ثبت نشده است.")
                return
            items = []
            for p in promises:
                target_str = "خودم"
                if p.receiver_id:
                    rec_stmt = select(User).where(User.telegram_id == p.receiver_id)
                    rec_res = await session.execute(rec_stmt)
                    rec = rec_res.scalar_one_or_none()
                    if rec: target_str = rec.display_name
                items.append(f"محتوای قول: {p.content}\nبه شخص: {target_str}\nتاریخ: {p.jalali_created_at}")
            await callback.message.edit_text("\n\n".join(items))
        elif list_type == "friends":
            stmt = select(Promise).where(Promise.receiver_id == callback.from_user.id, Promise.status == PromiseStatus.CONFIRMED)
            res = await session.execute(stmt)
            promises = res.scalars().all()
            if not promises:
                await callback.message.edit_text("هیچ قولی از طرف دوستان برای شما ثبت نشده است.")
                return
            items = []
            for p in promises:
                giver_stmt = select(User).where(User.telegram_id == p.giver_id)
                giver_res = await session.execute(giver_stmt)
                giver = giver_res.scalar_one_or_none()
                giver_str = giver.display_name if giver else "دوست"
                items.append(f"محتوای قول: {p.content}\nاز شخص: {giver_str}\nتاریخ: {p.jalali_created_at}")
            await callback.message.edit_text("\n\n".join(items))
