import logging
from aiogram import Router, types
from aiogram.filters import CommandStart, Command

logger = logging.getLogger(__name__)
router = Router(name="start_router")


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Handle /start command with user-friendly instructions."""
    user_name = message.from_user.first_name if message.from_user else "there"
    welcome_text = (
        f"👋 **Welcome, {user_name}!**\n\n"
        f"🎬 **Webseries & Movie Search Bot** (`Webseries_hitt_bot`)\n\n"
        f"Search and download movies and complete web series across multiple resolutions (480p, 720p, 1080p, 4K).\n\n"
        f"🔍 **How to use:**\n"
        f"Simply send the name of any **Movie** or **Web Series**.\n\n"
        f"_Example:_ `Inception` or `Breaking Bad`"
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command."""
    help_text = (
        "📖 **Help & Instructions**\n\n"
        "1. Send the title of the movie or TV show.\n"
        "2. Select the matching title from the buttons.\n"
        "3. Choose your desired season, episode, and video quality.\n"
        "4. Click the secure streaming / download link.\n\n"
        "⚠️ _Note: Ensure you are a member of our main channel to generate download links._"
    )
    await message.answer(help_text, parse_mode="Markdown")
