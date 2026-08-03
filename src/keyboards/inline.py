from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from src.config import settings

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=settings.MENU_OPTIONS["CREATE_PROMISE"]))
    builder.add(KeyboardButton(text=settings.MENU_OPTIONS["LIST_PROMISES"]))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    # Adding user_id to callback_data to ensure group chat safety
    builder = InlineKeyboardBuilder()
    builder.button(text="آره", callback_data=f"confirm_initial:yes:{user_id}")
    builder.button(text="نه", callback_data=f"confirm_initial:no:{user_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_target_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="خودم", callback_data=f"target:self:{user_id}")
    builder.button(text="دوستم", callback_data=f"target:friend:{user_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_receiver_approval_keyboard(promise_id: int, receiver_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅", callback_data=f"promise_appr:yes:{promise_id}:{receiver_id}")
    builder.button(text="❌", callback_data=f"promise_appr:no:{promise_id}:{receiver_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_list_promises_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="قول های من", callback_data=f"list_promises:my:{user_id}")
    builder.button(text="قول های دوستان", callback_data=f"list_promises:friends:{user_id}")
    builder.adjust(2)
    return builder.as_markup()
