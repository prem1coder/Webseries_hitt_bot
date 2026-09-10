import logging
from typing import Optional
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


def _parse_callback_id(data: str, expected_prefix: str) -> Optional[int]:
    """Safely parse integer ID from callback data with prefix check."""
    if not data or not data.startswith(f"{expected_prefix}:"):
        return None
    parts = data.split(":", 1)
    if len(parts) != 2:
        return None
    raw_id = parts[1].strip()
    if not raw_id.isdigit():
        return None
    parsed_id = int(raw_id)
    return parsed_id if parsed_id > 0 else None


@router.callback_query(F.data.startswith("content:"))
async def handle_content_selection(callback: types.CallbackQuery):
    """Handle clicking a movie or series from search results."""
    content_id = _parse_callback_id(callback.data, "content")
    if not content_id:
        await callback.answer("❌ Malformed content request.", show_alert=True)
        return

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
    season_id = _parse_callback_id(callback.data, "season")
    if not season_id:
        await callback.answer("❌ Malformed season request.", show_alert=True)
        return

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
    episode_id = _parse_callback_id(callback.data, "episode")
    if not episode_id:
        await callback.answer("❌ Malformed episode request.", show_alert=True)
        return

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
    """
    Handle selecting a file quality.
    SECURITY FLOW:
    1. Defensively parse callback data and reject malformed inputs.
    2. Load file and verify relationship integrity FIRST.
    3. Verify active channel membership.
    4. Issue signed download token ONLY after verifying file existence and membership.
    NOTE: Signed URL acts as a bearer capability for its TTL. Telegram identity is verified at issuance.
    """
    if not callback.data or ":" not in callback.data:
        await callback.answer("❌ Malformed request.", show_alert=True)
        return

    parts = callback.data.split(":", 1)
    prefix = parts[0]
    raw_file_id = parts[1].strip()

    if not raw_file_id.isdigit():
        await callback.answer("❌ Invalid file ID.", show_alert=True)
        return

    file_id = int(raw_file_id)
    if file_id <= 0:
        await callback.answer("❌ Invalid file ID.", show_alert=True)
        return

    user_id = callback.from_user.id

    async with get_db_session() as session:
        file_repo = FileRepository(session)
        file_obj = await file_repo.get_by_id(file_id)

        # Step 1: Prove resource exists and has integrity BEFORE checking membership
        if not file_obj or not file_obj.content:
            await callback.answer("❌ File not found or no longer available.", show_alert=True)
            return

        # Step 2: Check Channel Membership
        is_member = await MembershipService.check_membership(bot, user_id)

        if not is_member:
            invite_link = settings.MAIN_CHANNEL_INVITE_LINK
            if not invite_link or not invite_link.startswith("http"):
                logger.critical("MAIN_CHANNEL_INVITE_LINK is missing or not a valid URL. Refusing fallback.")
                await callback.answer(
                    "❌ Channel configuration error. Please contact the administrator.",
                    show_alert=True
                )
                return

            if prefix == "verify":
                await callback.answer("❌ You have not joined the channel yet! Please join first.", show_alert=True)
            else:
                await callback.answer()

            text = (
                "⚠️ **Channel Membership Required**\n\n"
                "To access high-speed streaming and downloads, please join our official Telegram channel first.\n\n"
                "After joining, click **'Verify Membership'** below!"
            )
            keyboard = membership_required_keyboard(invite_link, file_id)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            return

        # Step 3: Member verified and file verified -> Issue secure expiring bearer token
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
