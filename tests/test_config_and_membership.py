import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.enums import ChatMemberStatus
from database.config import Settings
from bot.services.membership import MembershipService


def test_settings_channel_id_types():
    """Verify Settings accepts numeric channel IDs and stores values."""
    s1 = Settings(ARCHIVE_CHANNEL_ID=-1001234567890, MAIN_CHANNEL_ID=-1009876543210)
    assert s1.ARCHIVE_CHANNEL_ID == -1001234567890
    assert s1.MAIN_CHANNEL_ID == -1009876543210


def test_production_validation_rejects_missing_credentials():
    """Verify production settings validation rejects empty BOT_TOKEN, API credentials, and channel IDs."""
    s = Settings(
        ENVIRONMENT="production",
        BOT_TOKEN="",
        TELEGRAM_API_ID=0,
        TELEGRAM_API_HASH="",
        DOWNLOAD_SECRET="a_very_strong_random_secret_with_more_than_32_characters_12345"
    )
    with pytest.raises(ValueError, match="Production requires a valid BOT_TOKEN"):
        s.validate_for_environment()


def test_production_validation_rejects_weak_or_default_secret():
    """Verify production settings validation rejects default or short secrets."""
    s = Settings(
        ENVIRONMENT="production",
        BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        TELEGRAM_API_ID=123456,
        TELEGRAM_API_HASH="0123456789abcdef0123456789abcdef",
        ARCHIVE_CHANNEL_ID=-1001234567890,
        MAIN_CHANNEL_ID=-1009876543210,
        MAIN_CHANNEL_INVITE_LINK="https://t.me/+validinvite",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/webseries_db",
        DOWNLOAD_SECRET="default_dev_secret_change_in_production"
    )
    with pytest.raises(ValueError, match="Production requires a strong, random DOWNLOAD_SECRET"):
        s.validate_for_environment()

    # Short secret
    s.DOWNLOAD_SECRET = "short_secret_under_32"
    with pytest.raises(ValueError, match="Production requires a strong, random DOWNLOAD_SECRET"):
        s.validate_for_environment()


def test_production_validation_rejects_invalid_channel_ids():
    """Verify production rejects zero or positive channel IDs."""
    base_kwargs = dict(
        ENVIRONMENT="production",
        BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        TELEGRAM_API_ID=123456,
        TELEGRAM_API_HASH="0123456789abcdef0123456789abcdef",
        MAIN_CHANNEL_INVITE_LINK="https://t.me/+validinvite",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/webseries_db",
        DOWNLOAD_SECRET="a_very_strong_random_secret_with_more_than_32_characters_12345"
    )
    # Zero channel ID
    s_zero = Settings(ARCHIVE_CHANNEL_ID=0, MAIN_CHANNEL_ID=-1001234567890, **base_kwargs)
    with pytest.raises(ValueError, match="Production requires ARCHIVE_CHANNEL_ID to be set"):
        s_zero.validate_for_environment()

    # Positive channel ID
    s_pos = Settings(ARCHIVE_CHANNEL_ID=-1001234567890, MAIN_CHANNEL_ID=123456789, **base_kwargs)
    with pytest.raises(ValueError, match="Production requires MAIN_CHANNEL_ID to be a numeric Telegram channel ID"):
        s_pos.validate_for_environment()


def test_production_validation_rejects_invalid_ttl():
    """Verify production rejects invalid token TTL bounds."""
    base_kwargs = dict(
        ENVIRONMENT="production",
        BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        TELEGRAM_API_ID=123456,
        TELEGRAM_API_HASH="0123456789abcdef0123456789abcdef",
        ARCHIVE_CHANNEL_ID=-1001234567890,
        MAIN_CHANNEL_ID=-1009876543210,
        MAIN_CHANNEL_INVITE_LINK="https://t.me/+validinvite",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/webseries_db",
        DOWNLOAD_SECRET="a_very_strong_random_secret_with_more_than_32_characters_12345"
    )
    s_low = Settings(TOKEN_EXPIRY_MINUTES=0, **base_kwargs)
    with pytest.raises(ValueError, match="TOKEN_EXPIRY_MINUTES must be between"):
        s_low.validate_for_environment()

    s_high = Settings(TOKEN_EXPIRY_MINUTES=2000, **base_kwargs)
    with pytest.raises(ValueError, match="TOKEN_EXPIRY_MINUTES must be between"):
        s_high.validate_for_environment()


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
async def test_membership_restricted_user(monkeypatch):
    """Verify restricted members are verified via is_member attribute."""
    fake_settings = Settings(MAIN_CHANNEL_ID=-1001234567890)
    monkeypatch.setattr("bot.services.membership.get_settings", lambda: fake_settings)

    mock_bot = AsyncMock()

    # Restricted but still in channel (is_member=True)
    mock_member_in = MagicMock()
    mock_member_in.status = ChatMemberStatus.RESTRICTED
    mock_member_in.is_member = True
    mock_bot.get_chat_member.return_value = mock_member_in
    assert await MembershipService.check_membership(mock_bot, user_id=12345) is True

    # Restricted and kicked / banned (is_member=False)
    mock_member_out = MagicMock()
    mock_member_out.status = ChatMemberStatus.RESTRICTED
    mock_member_out.is_member = False
    mock_bot.get_chat_member.return_value = mock_member_out
    assert await MembershipService.check_membership(mock_bot, user_id=12345) is False


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
