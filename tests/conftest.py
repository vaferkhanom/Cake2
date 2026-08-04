"""Test fixtures and helpers for Promise Bot tests."""

from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery, User as TgUser, Chat
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext


def make_message(text: str = "", user_id: int = 100, chat_id: int = None) -> Message:
    """Create a mock Message object."""
    if chat_id is None:
        chat_id = user_id

    message = MagicMock(spec=Message)
    message.text = text
    message.message_id = 12345
    message.date = MagicMock()

    # User
    from_user = MagicMock(spec=TgUser)
    from_user.id = user_id
    from_user.username = f"user{user_id}"
    from_user.full_name = f"User {user_id}"
    from_user.is_bot = False
    message.from_user = from_user

    # Chat
    chat = MagicMock(spec=Chat)
    chat.id = chat_id
    chat.type = "private"
    message.chat = chat

    # Bot
    bot = AsyncMock()
    message.bot = bot

    # Answer/edit methods
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    message.reply = AsyncMock()

    return message


def make_callback(callback_data: str, user_id: int = 100, full_name: str = None, username: str = None) -> CallbackQuery:
    """Create a mock CallbackQuery object."""
    callback = MagicMock(spec=CallbackQuery)
    callback.data = callback_data
    callback.id = "test_callback_id"

    # User
    from_user = MagicMock(spec=TgUser)
    from_user.id = user_id
    from_user.username = username or f"user{user_id}"
    from_user.full_name = full_name or f"User {user_id}"
    from_user.is_bot = False
    callback.from_user = from_user

    # Message (the message the button was on)
    message = MagicMock()
    message.message_id = 12345
    message.chat = MagicMock()
    message.chat.id = user_id
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    callback.message = message

    # Bot
    bot = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.send_message = AsyncMock()
    callback.bot = bot

    # Answer method
    callback.answer = AsyncMock()

    return callback


def make_fsm():
    """Create a fresh FSMContext with MemoryStorage."""
    storage = MemoryStorage()
    return FSMContext(storage=storage, key=("chat", "user"))