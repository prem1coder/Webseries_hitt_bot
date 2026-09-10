import logging
from typing import Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from database.config import get_settings

logger = logging.getLogger(__name__)


class MembershipService:
    @staticmethod
    def get_target_channel_id() -> Optional[int]:
        """Validate and return canonical numeric MAIN_CHANNEL_ID, or None if invalid/missing."""
        settings = get_settings()
        channel_id = settings.MAIN_CHANNEL_ID

        if not channel_id:
            logger.error("Configuration error: MAIN_CHANNEL_ID is not set.")
            return None

        if isinstance(channel_id, str):
            clean_str = channel_id.strip()
            if clean_str.startswith("http://") or clean_str.startswith("https://") or clean_str.startswith("t.me/"):
                logger.error(
                    f"Configuration error: MAIN_CHANNEL_ID is set to an invite URL ({clean_str}). "
                    "Telegram Bot API requires a numeric channel ID (e.g. -100xxxxxxxxxx)."
                )
                return None
            try:
                return int(clean_str)
            except ValueError:
                logger.error(f"Configuration error: MAIN_CHANNEL_ID '{clean_str}' is not a valid numeric ID.")
                return None

        if isinstance(channel_id, int):
            if channel_id == 0:
                logger.error("Configuration error: MAIN_CHANNEL_ID is unset (0).")
                return None
            return channel_id

        logger.error(f"Configuration error: MAIN_CHANNEL_ID has invalid type: {type(channel_id)}")
        return None

    @classmethod
    async def check_membership(cls, bot: Bot, user_id: int) -> bool:
        """
        Verify if the given user is an active member or administrator of MAIN_CHANNEL_ID.
        Always fails closed (returns False on any configuration error, API failure, or non-member status).
        """
        target_chat_id = cls.get_target_channel_id()
        if target_chat_id is None:
            return False

        try:
            member = await bot.get_chat_member(chat_id=target_chat_id, user_id=user_id)

            if member.status in {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER}:
                return True

            if member.status == ChatMemberStatus.RESTRICTED:
                # Allow restricted status only if Telegram confirms user is still an active member
                is_member = getattr(member, "is_member", False)
                if is_member:
                    return True
                logger.info(f"User {user_id} in {target_chat_id} is restricted but is_member is False. Access denied.")
                return False

            logger.info(f"User {user_id} in {target_chat_id} has status '{member.status}'. Access denied.")
            return False

        except Exception as e:
            logger.error(f"Telegram API error checking membership for user {user_id} in channel {target_chat_id}: {e}")
            return False
