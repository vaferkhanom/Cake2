import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats
from src.config import settings
from src.database.session import init_db
from src.handlers import promise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="شروع و منوی اصلی"),
    BotCommand(command="new", description="ثبت قول جدید"),
    BotCommand(command="promises", description="لیست قول‌ها"),
    BotCommand(command="profile", description="پروفایل و امتیاز"),
    BotCommand(command="help", description="راهنما"),
]

GROUP_COMMANDS = [
    BotCommand(command="promise", description="ثبت قول برای یه عضو گروه (با تگ @username یا ریپلای)"),
    BotCommand(command="help", description="راهنمای استفاده در گروه"),
]


async def main():
    logger.info("Initializing database...")
    await init_db()

    logger.info("Starting bot...")
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(promise.router)

    # TODO: Implement periodic expiry job for promises with deadlines
    # This job should run every N minutes and:
    # 1. Find promises where deadline < now AND status IN ('confirmed', 'claimed_done')
    # 2. Update status to EXPIRED
    # 3. Call apply_expired_score() for each
    # 4. Notify givers about expired promises
    # Note: apply_expired_score exists in src/services/scoring.py but is never called
    # Implementation options:
    # - asyncio.create_task with a loop + asyncio.sleep
    # - apscheduler (add to requirements.txt)
    # - Celery/Redis for production-scale deployment

    await bot.set_my_commands(COMMANDS)
    await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
