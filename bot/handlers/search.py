import html
import logging
from aiogram import Router, types, F
from database.connection import get_db_session
from database.repositories.content_repo import ContentRepository
from bot.keyboards.inline import search_results_keyboard

logger = logging.getLogger(__name__)
router = Router(name="search_router")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search_query(message: types.Message):
    """Handle text search queries against PostgreSQL normalized titles."""
    query = message.text.strip()
    if not query or len(query) < 2:
        await message.answer("⚠️ Please enter at least 2 characters to search.")
        return

    safe_query = html.escape(query)

    async with get_db_session() as session:
        content_repo = ContentRepository(session)
        results = await content_repo.search_by_title(query, limit=15)

    if not results:
        not_found_text = (
            f"❌ <b>No results found for:</b> <code>{safe_query}</code>\n\n"
            f"💡 <b>Tips:</b>\n"
            f"• Check the spelling\n"
            f"• Try searching with the series/movie title only (e.g., <code>Loki</code> instead of <code>Loki Season 2 Ep 3</code>)"
        )
        await message.answer(not_found_text, parse_mode="HTML")
        return

    search_text = f"🔎 <b>Found {len(results)} result(s) for:</b> <code>{safe_query}</code>\n\n<i>Please select from below:</i>"
    keyboard = search_results_keyboard(results)
    await message.answer(search_text, reply_markup=keyboard, parse_mode="HTML")
