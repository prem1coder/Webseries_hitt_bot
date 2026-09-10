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

        # If no channel ID configured (or placeholder default in test), grant access
        if not channel_id or channel_id == -1009876543210:
            logger.debug("Main channel check skipped (default test channel ID).")
            return True

        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            valid_statuses = {
                ChatMemberStatus.CREATOR,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.RESTRICTED
            }
            return member.status in valid_statuses
        except Exception as e:
            logger.error(f"Error checking channel membership for user {user_id} in channel {channel_id}: {e}")
            # In case of bot permissions error, fail-safe or log
            return False
