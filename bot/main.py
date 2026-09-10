import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database.config import get_settings
from database.connection import init_db
from bot.handlers import start_router, search_router, callbacks_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bot")


async def main():
    settings = get_settings()

    logger.info("Initializing database schema...")
    await init_db()

    logger.info("Starting Telegram Bot (Webseries_hitt_bot)...")
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Register handlers
    dp.include_router(start_router)
    dp.include_router(search_router)
    dp.include_router(callbacks_router)

    logger.info("Bot started and listening for updates...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
