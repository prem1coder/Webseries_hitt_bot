import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database.config import get_settings
from database.connection import check_db_ready, dispose_engine
from bot.handlers import start_router, search_router, callbacks_router
from bot.services.membership import MembershipService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bot")


async def main():
    settings = get_settings()
    settings.validate_for_environment()

    if not settings.BOT_TOKEN:
        logger.critical("Fatal: BOT_TOKEN is not set in environment or configuration.")
        raise ValueError("BOT_TOKEN is required to start the bot.")

    main_channel_id = MembershipService.get_target_channel_id()
    if main_channel_id is None:
        logger.warning(
            "MAIN_CHANNEL_ID is not configured as a valid numeric Telegram chat ID. "
            "Membership verification will fail-closed for all users until configured."
        )
    else:
        logger.info(f"Configured MAIN_CHANNEL_ID for membership verification: {main_channel_id}")

    logger.info("Checking database readiness...")
    await check_db_ready()
    logger.info("Database schema and connectivity verified.")

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

    try:
        logger.info("Bot started and listening for updates...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Shutting down bot and disposing database engine...")
        await bot.session.close()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
