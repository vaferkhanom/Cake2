"""Telegram notifier adapter — translates domain-layer notifications into
aiogram messages. This is the ONLY place that knows how to reach users via
Telegram; the domain layer (src/domain/promise_actions.py) just declares
"something happened".

The bot handlers use this adapter; the FastAPI backend uses a no-op notifier
(or a queue) and lets the bot deliver the messages.
"""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from src.domain.promise_actions import PromiseNotifier
from src.database.models import Promise
from src.keyboards.inline import receiver_confirm_keyboard, receiver_confirm_done_keyboard
from src.utils.format import escape_html, make_mention

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Delivers domain notifications as Telegram messages."""

    def __init__(self, bot: Bot):
        self.bot = bot

    # ── helpers ────────────────────────────────────────────────────────────

    async def _edit_or_send(
        self,
        chat_id: int,
        text: str,
        message_id: int | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        """Prefer editing message_id in chat_id; fall back to sending new."""
        if message_id:
            try:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                )
                return
            except Exception as e:
                logger.warning("edit_message_text failed (%s/%s): %s", chat_id, message_id, e)
        try:
            await self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            logger.warning("send_message failed (%s): %s", chat_id, e)

    # ── domain notifications ───────────────────────────────────────────────

    async def on_promise_created(self, promise: Promise, giver_name: str, invite_link: str | None = None) -> None:
        if invite_link:
            # Receiver unknown — give the giver an invite link to forward
            await self.bot.send_message(
                chat_id=promise.giver_id,
                text=(
                    f"هنوز {escape_html(giver_name)} با من آشنا نشده 😅\n"
                    f"این لینک رو براش بفرست تا قولت بهش برسه:\n{invite_link}"
                ),
            )
        elif promise.target_type.value == "friend" and promise.receiver_id:
            await self.bot.send_message(
                chat_id=promise.receiver_id,
                text=(
                    f"{escape_html(giver_name)} 🫵 می‌خواد بهت یه قول بده:\n"
                    f"<blockquote>{escape_html(promise.content)}</blockquote>\n\n"
                    f"قبول داری؟"
                ),
                reply_markup=receiver_confirm_keyboard(promise.id),
            )

    async def on_promise_accepted(self, promise: Promise, acceptor_name: str) -> None:
        text = (
            f"🎉 {escape_html(acceptor_name)} قول #{promise.promise_id or promise.id} رو تایید کرد:\n"
            f"<blockquote>{escape_html(promise.content)}</blockquote>"
        )
        await self._edit_or_send(
            chat_id=promise.giver_id,
            text=text,
            message_id=promise.giver_pending_message_id,
        )

    async def on_promise_rejected(
        self,
        promise_id: int,
        giver_id: int,
        content: str,
        rejector_name: str,
        giver_pending_message_id: int | None = None,
        giver_pending_chat_id: int | None = None,
    ) -> None:
        text = (
            f"❌ {escape_html(rejector_name)} قول #{promise_id} رو رد کرد:\n"
            f"<blockquote>{escape_html(content)}</blockquote>"
        )
        await self._edit_or_send(
            chat_id=giver_id,
            text=text,
            message_id=giver_pending_message_id,
        )

    async def on_claimed_done(self, promise: Promise, giver_name: str) -> None:
        if not promise.receiver_id:
            return
        text = (
            f"⚠️ {make_mention(promise.giver_id, giver_name)} می‌گه قول #{promise.promise_id or promise.id} رو انجام داده:\n\n"
            f"<blockquote>{escape_html(promise.content)}</blockquote>\n\n"
            f"تایید می‌کنی؟"
        )
        await self.bot.send_message(
            chat_id=promise.receiver_id,
            text=text,
            reply_markup=receiver_confirm_done_keyboard(promise.id),
        )

    async def on_confirm_done(self, promise: Promise, confirmer_name: str) -> None:
        text = f"🎉 {make_mention(promise.receiver_id, confirmer_name)} تایید کرد که قول #{promise.promise_id or promise.id} انجام شده!"
        if promise.giver_claim_message_id and promise.giver_claim_chat_id:
            try:
                await self.bot.edit_message_text(
                    chat_id=promise.giver_claim_chat_id,
                    message_id=promise.giver_claim_message_id,
                    text=text,
                )
                return
            except Exception as e:
                logger.warning("edit giver claim msg failed: %s", e)
        try:
            await self.bot.send_message(chat_id=promise.giver_id, text=text)
        except Exception as e:
            logger.warning("send to giver failed: %s", e)

    async def on_disputed(self, promise: Promise, disputer_name: str) -> None:
        text = (
            f"⚠️ {make_mention(promise.receiver_id, disputer_name)} ادعای انجام قول #{promise.promise_id or promise.id} رو رد کرد.\n"
            f"وضعیت: DISPUTED\n"
            f"می‌تونی با طرف مقابل صحبت کنی و دوباره ادعا کنی."
        )
        if promise.giver_claim_message_id and promise.giver_claim_chat_id:
            try:
                await self.bot.edit_message_text(
                    chat_id=promise.giver_claim_chat_id,
                    message_id=promise.giver_claim_message_id,
                    text=text,
                )
                return
            except Exception as e:
                logger.warning("edit giver claim msg (dispute) failed: %s", e)
        try:
            await self.bot.send_message(chat_id=promise.giver_id, text=text)
        except Exception as e:
            logger.warning("send to giver (dispute) failed: %s", e)

    async def on_broken(self, promise: Promise) -> None:
        if promise.receiver_id and promise.receiver_id != promise.giver_id:
            try:
                await self.bot.send_message(
                    chat_id=promise.receiver_id,
                    text=(
                        f"💔 قول #{promise.promise_id or promise.id} توسط قول‌دهنده به عنوان نقض‌شده ثبت شد:\n"
                        f"<blockquote>{escape_html(promise.content)}</blockquote>"
                    ),
                )
            except Exception as e:
                logger.warning("send to receiver (broken) failed: %s", e)

    async def on_resolved(self, promise: Promise) -> None:
        try:
            await self.bot.send_message(
                chat_id=promise.giver_id,
                text=f"✅ قول #{promise.promise_id or promise.id} توسط گیرنده تایید شد (مخالفیت حل شد).",
            )
        except Exception as e:
            logger.warning("send to giver (resolved) failed: %s", e)

    async def on_expired(self, promise: Promise) -> None:
        try:
            await self.bot.send_message(
                chat_id=promise.giver_id,
                text=(
                    f"⏰ قول #{promise.promise_id or promise.id} به دلیل گذشتن مهلت منقضی شد:\n"
                    f"<blockquote>{escape_html(promise.content)}</blockquote>"
                ),
            )
        except Exception as e:
            logger.warning("send to giver (expired) failed: %s", e)


class BotNotifierAdapter(TelegramNotifier):
    """Backwards-compatible alias."""


def build_notifier(bot: Bot) -> PromiseNotifier:
    return TelegramNotifier(bot)
