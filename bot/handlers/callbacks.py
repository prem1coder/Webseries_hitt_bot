import logging
from aiogram import Router, types, F, Bot
from database.config import get_settings
from database.connection import get_db_session
from database.repositories.content_repo import ContentRepository
from database.repositories.file_repo import FileRepository
from bot.services.membership import MembershipService
from web.services.token_service import TokenService
from bot.keyboards.inline import (
    movie_qualities_keyboard,
    series_seasons_keyboard,
    season_episodes_keyboard,
    episode_qualities_keyboard,
    membership_required_keyboard,
    download_ready_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="callbacks_router")
settings = get_settings()


@router.callback_query(F.data.startswith("content:"))
async def handle_content_selection(callback: types.CallbackQuery):
    """Handle clicking a movie or series from search results."""
    content_id = int(callback.data.split(":")[1])

    async with get_db_session() as session:
        content_repo = ContentRepository(session)
        content = await content_repo.get_by_id(content_id)

        if not content:
            await callback.answer("❌ Content not found.", show_alert=True)
            return

        year_str = f" ({content.year})" if content.year else ""

        if content.content_type == "movie":
            files = await content_repo.get_movie_qualities(content.id)
            if not files:
                await callback.answer("⚠️ No files currently available for this movie.", show_alert=True)
                return

            text = (
                f"🎬 **{content.title}**{year_str}\n\n"
                f"📝 {content.description or 'No synopsis available.'}\n\n"
                f"✨ **Select your desired video quality:**"
            )
            keyboard = movie_qualities_keyboard(content.id, files)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

        else:  # Series
            seasons = await content_repo.get_series_seasons(content.id)
            if not seasons:
                await callback.answer("⚠️ No seasons found for this series.", show_alert=True)
                return

            text = (
                f"📺 **{content.title}**{year_str}\n\n"
                f"📝 {content.description or 'No synopsis available.'}\n\n"
                f"📁 **Select a Season:**"
            )
            keyboard = series_seasons_keyboard(content.id, seasons)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer()


@router.callback_query(F.data.startswith("season:"))
async def handle_season_selection(callback: types.CallbackQuery):
    """Handle clicking a season in a series."""
    season_id = int(callback.data.split(":")[1])

    async with get_db_session() as session:
        content_repo = ContentRepository(session)
        season = await content_repo.get_season_by_id(season_id)

        if not season:
            await callback.answer("❌ Season not found.", show_alert=True)
            return

        episodes = await content_repo.get_season_episodes(season.id)
        if not episodes:
            await callback.answer("⚠️ No episodes found in this season.", show_alert=True)
            return

        text = (
            f"📁 **{season.title or f'Season {season.season_number}'}**\n\n"
            f"▶️ **Select an Episode:**"
        )
        keyboard = season_episodes_keyboard(season.content_id, season.id, episodes)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer()


@router.callback_query(F.data.startswith("episode:"))
async def handle_episode_selection(callback: types.CallbackQuery):
    """Handle clicking an episode in a season."""
    episode_id = int(callback.data.split(":")[1])

    async with get_db_session() as session:
        content_repo = ContentRepository(session)
        episode = await content_repo.get_episode_by_id(episode_id)

        if not episode:
            await callback.answer("❌ Episode not found.", show_alert=True)
            return

        files = await content_repo.get_episode_qualities(episode.id)
        if not files:
            await callback.answer("⚠️ No qualities available for this episode.", show_alert=True)
            return

        dur_str = f" • Duration: {episode.duration_seconds // 60}m" if episode.duration_seconds else ""
        text = (
            f"▶️ **{episode.title or f'Episode {episode.episode_number}'}**{dur_str}\n\n"
            f"✨ **Select your desired video quality:**"
        )
        keyboard = episode_qualities_keyboard(episode.season_id, files)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer()


@router.callback_query(F.data.startswith("file:") | F.data.startswith("verify:"))
async def handle_file_selection(callback: types.CallbackQuery, bot: Bot):
    """Handle selecting a file quality with mandatory channel membership check."""
    prefix, file_id_str = callback.data.split(":", 1)
    file_id = int(file_id_str)
    user_id = callback.from_user.id

    # 1. Check Channel Membership
    is_member = await MembershipService.check_membership(bot, user_id)

    if not is_member:
        if prefix == "verify":
            await callback.answer("❌ You have not joined the channel yet! Please join first.", show_alert=True)
        else:
            await callback.answer()

        invite_link = settings.MAIN_CHANNEL_INVITE_LINK or "https://t.me"
        text = (
            "⚠️ **Channel Membership Required**\n\n"
            "To access high-speed streaming and downloads, please join our official Telegram channel first.\n\n"
            "After joining, click **'Verify Membership'** below!"
        )
        keyboard = membership_required_keyboard(invite_link, file_id)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    # 2. Member verified -> Generate secure expiring download token
    async with get_db_session() as session:
        file_repo = FileRepository(session)
        file_obj = await file_repo.get_by_id(file_id)

        if not file_obj:
            await callback.answer("❌ File not found.", show_alert=True)
            return

        token = TokenService.generate_download_token(file_id=file_obj.id, user_id=user_id)
        download_url = f"{settings.base_web_url}/download/{token}"

        size_mb = f"{file_obj.file_size_bytes / (1024 * 1024):.1f} MB" if file_obj.file_size_bytes else "Unknown"
        audio_str = f"\n🔊 Audio: `{file_obj.audio}`" if file_obj.audio else ""

        text = (
            f"✅ **Your Secure Download Link Is Ready!**\n\n"
            f"📄 **File:** `{file_obj.file_name}`\n"
            f"📊 **Size:** `{size_mb}` | **Quality:** `{file_obj.quality or 'HD'}`{audio_str}\n\n"
            f"⏱ _This link is valid for {settings.TOKEN_EXPIRY_MINUTES} minutes._"
        )
        keyboard = download_ready_keyboard(download_url)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

    await callback.answer("✅ Link generated!")
