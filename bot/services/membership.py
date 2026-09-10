import logging
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from database.config import get_settings

logger = logging.getLogger(__name__)


class MembershipService:
    @staticmethod
    async def check_membership(bot: Bot, user_id: int) -> bool:
        """
        Verify if the given user is an active member or administrator of MAIN_CHANNEL_ID.
        Returns True if authorized, False otherwise.
        """
        settings = get_settings()
        channel_id = settings.MAIN_CHANNEL_ID

        # If no channel ID configured or default placeholder
        if not channel_id or channel_id == -1009876543210:
            logger.debug("Main channel check skipped (default test channel ID).")
            return True

        # Handle numeric vs URL channel_id
        target_chat_id = channel_id
        if isinstance(channel_id, str):
            clean_str = channel_id.strip()
            if clean_str.startswith("http://") or clean_str.startswith("https://") or clean_str.startswith("t.me/"):
                logger.warning(
                    f"MAIN_CHANNEL_ID is set to an invite URL ({clean_str}). "
                    "Telegram Bot API requires numeric channel ID (e.g. -1001234567890) for member verification. "
                    "Bypassing strict check to avoid blocking user."
                )
                return True
            try:
                target_chat_id = int(clean_str)
            except ValueError:
                target_chat_id = clean_str

        try:
            member = await bot.get_chat_member(chat_id=target_chat_id, user_id=user_id)
            valid_statuses = {
                ChatMemberStatus.CREATOR,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.RESTRICTED
            }
            return member.status in valid_statuses
        except Exception as e:
            logger.error(f"Error checking channel membership for user {user_id} in channel {target_chat_id}: {e}")
            # Fail-safe: if bot is not admin or channel chat ID invalid, log error
            return False
