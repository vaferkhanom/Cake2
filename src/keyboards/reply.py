"""Reply keyboards for Promise Bot."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard with 3 options."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🤝 ثبت یه قول جدید"))
    builder.add(KeyboardButton(text="📋 قول‌های من"))
    builder.add(KeyboardButton(text="👤 پروفایل من"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)