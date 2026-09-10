from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Content, Season, Episode, File


def search_results_keyboard(contents: List[Content]) -> InlineKeyboardMarkup:
    """Inline keyboard for search results."""
    buttons = []
    for item in contents:
        icon = "🎬" if item.content_type == "movie" else "📺"
        year_str = f" ({item.year})" if item.year else ""
        btn_text = f"{icon} {item.title}{year_str}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"content:{item.id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


import re


def _quality_sort_key(file_obj: File) -> int:
    """Sort key for numeric quality ordering (2160p > 1080p > 720p > 480p > Unknown)."""
    q = (file_obj.quality or "").lower()
    match = re.search(r"(\d+)", q)
    if match:
        return int(match.group(1))
    return 0


def movie_qualities_keyboard(content_id: int, files: List[File]) -> InlineKeyboardMarkup:
    """Inline keyboard showing available qualities for a movie, ordered by resolution descending."""
    sorted_files = sorted(files, key=_quality_sort_key, reverse=True)
    row = []
    keyboard = []
    for f in sorted_files:
        size_mb = f" ({f.file_size_bytes // (1024 * 1024)}MB)" if f.file_size_bytes else ""
        label = f.quality if f.quality and f.quality != "Unknown" else "Watch HD"
        row.append(InlineKeyboardButton(text=f"📥 {label}{size_mb}", callback_data=f"file:{f.id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Navigation buttons
    keyboard.append([InlineKeyboardButton(text="🔍 New Search", switch_inline_query_current_chat="")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def series_seasons_keyboard(content_id: int, seasons: List[Season]) -> InlineKeyboardMarkup:
    """Inline keyboard showing available seasons for a series."""
    row = []
    keyboard = []
    for s in seasons:
        row.append(InlineKeyboardButton(text=f"📁 Season {s.season_number}", callback_data=f"season:{s.id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔍 New Search", switch_inline_query_current_chat="")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def season_episodes_keyboard(content_id: int, season_id: int, episodes: List[Episode]) -> InlineKeyboardMarkup:
    """Inline keyboard showing available episodes for a season."""
    row = []
    keyboard = []
    for ep in episodes:
        btn_text = f"▶️ Ep {ep.episode_number}"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"episode:{ep.id}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Back to Seasons button
    keyboard.append([InlineKeyboardButton(text="⬅️ Back to Seasons", callback_data=f"content:{content_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def episode_qualities_keyboard(season_id: int, files: List[File]) -> InlineKeyboardMarkup:
    """Inline keyboard showing available qualities for an episode, ordered by resolution descending."""
    sorted_files = sorted(files, key=_quality_sort_key, reverse=True)
    row = []
    keyboard = []
    for f in sorted_files:
        size_mb = f" ({f.file_size_bytes // (1024 * 1024)}MB)" if f.file_size_bytes else ""
        label = f.quality if f.quality and f.quality != "Unknown" else "Watch HD"
        row.append(InlineKeyboardButton(text=f"📥 {label}{size_mb}", callback_data=f"file:{f.id}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Back to Episodes button
    keyboard.append([InlineKeyboardButton(text="⬅️ Back to Episodes", callback_data=f"season:{season_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def membership_required_keyboard(invite_link: str, file_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard prompting user to join channel and verify."""
    buttons = [
        [InlineKeyboardButton(text="📢 Join Main Channel", url=invite_link)],
        [InlineKeyboardButton(text="🔄 Verify Membership", callback_data=f"verify:{file_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def download_ready_keyboard(download_url: str, back_callback: Optional[str] = None) -> InlineKeyboardMarkup:
    """Inline keyboard with fast web streaming / download link."""
    buttons = [
        [InlineKeyboardButton(text="🚀 Download / Stream Video", url=download_url)]
    ]
    if back_callback:
        buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
