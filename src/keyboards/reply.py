"""Reply Keyboards for persistent bottom menu."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom menu — always accessible, independent of chat history."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🤝 ثبت قول جدید"))
    builder.add(KeyboardButton(text="📋 قول‌های من"))
    builder.add(KeyboardButton(text="👤 پروفایل من"))
    builder.add(KeyboardButton(text="📖 راهنما"))
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)