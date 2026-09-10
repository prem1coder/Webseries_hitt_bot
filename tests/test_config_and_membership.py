import pytest
from unittest.mock import AsyncMock
from database.config import Settings
from bot.services.membership import MembershipService


def test_settings_channel_id_types():
    """Verify Settings accepts both numeric channel IDs and invite URLs."""
    s1 = Settings(ARCHIVE_CHANNEL_ID=-1001234567890, MAIN_CHANNEL_ID=-1009876543210)
    assert s1.ARCHIVE_CHANNEL_ID == -1001234567890
    assert s1.MAIN_CHANNEL_ID == -1009876543210

    s2 = Settings(
        ARCHIVE_CHANNEL_ID="https://t.me/+dUcRmnREmc8xMWE5",
        MAIN_CHANNEL_ID="https://t.me/+JgKOf54r7A4yYTY1"
    )
    assert s2.ARCHIVE_CHANNEL_ID == "https://t.me/+dUcRmnREmc8xMWE5"
    assert s2.MAIN_CHANNEL_ID == "https://t.me/+JgKOf54r7A4yYTY1"


@pytest.mark.asyncio
async def test_membership_check_invite_url(monkeypatch):
    """Verify membership check bypasses strict check if MAIN_CHANNEL_ID is a URL."""
    fake_settings = Settings(MAIN_CHANNEL_ID="https://t.me/+JgKOf54r7A4yYTY1")
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()
    result = await MembershipService.check_membership(mock_bot, user_id=12345)
    assert result is True
    mock_bot.get_chat_member.assert_not_called()
