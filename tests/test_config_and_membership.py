import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.enums import ChatMemberStatus
from database.config import Settings
from bot.services.membership import MembershipService


def test_settings_channel_id_types():
    """Verify Settings accepts numeric channel IDs and stores string values."""
    s1 = Settings(ARCHIVE_CHANNEL_ID=-1001234567890, MAIN_CHANNEL_ID=-1009876543210)
    assert s1.ARCHIVE_CHANNEL_ID == -1001234567890
    assert s1.MAIN_CHANNEL_ID == -1009876543210


@pytest.mark.asyncio
async def test_membership_denied_when_channel_id_is_url(monkeypatch):
    """Verify membership check fails closed (returns False) when MAIN_CHANNEL_ID is a URL."""
    fake_settings = Settings(MAIN_CHANNEL_ID="https://t.me/+JgKOf54r7A4yYTY1")
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()
    result = await MembershipService.check_membership(mock_bot, user_id=12345)
    assert result is False
    mock_bot.get_chat_member.assert_not_called()


@pytest.mark.asyncio
async def test_membership_denied_when_channel_id_missing(monkeypatch):
    """Verify membership check fails closed when MAIN_CHANNEL_ID is empty/unset."""
    fake_settings = Settings(MAIN_CHANNEL_ID="")
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()
    result = await MembershipService.check_membership(mock_bot, user_id=12345)
    assert result is False
    mock_bot.get_chat_member.assert_not_called()


@pytest.mark.asyncio
async def test_membership_denied_on_api_error(monkeypatch):
    """Verify membership check fails closed when Telegram API raises an exception."""
    fake_settings = Settings(MAIN_CHANNEL_ID=-1001234567890)
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()
    mock_bot.get_chat_member.side_effect = Exception("Chat not found or Bot not admin")

    result = await MembershipService.check_membership(mock_bot, user_id=12345)
    assert result is False
    mock_bot.get_chat_member.assert_called_once_with(chat_id=-1001234567890, user_id=12345)


@pytest.mark.asyncio
async def test_membership_denied_for_non_member(monkeypatch):
    """Verify membership check denies users who left or were kicked."""
    fake_settings = Settings(MAIN_CHANNEL_ID=-1001234567890)
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()
    mock_member = MagicMock()
    mock_member.status = ChatMemberStatus.LEFT
    mock_bot.get_chat_member.return_value = mock_member

    result = await MembershipService.check_membership(mock_bot, user_id=12345)
    assert result is False


@pytest.mark.asyncio
async def test_membership_allowed_for_valid_member(monkeypatch):
    """Verify active members, admins, and creators are granted access."""
    fake_settings = Settings(MAIN_CHANNEL_ID=-1001234567890)
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()

    for allowed_status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
        mock_member = MagicMock()
        mock_member.status = allowed_status
        mock_bot.get_chat_member.return_value = mock_member

        result = await MembershipService.check_membership(mock_bot, user_id=12345)
        assert result is True
