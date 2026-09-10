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

    async with get_db_session() as session:
        content_repo = ContentRepository(session)
        results = await content_repo.search_by_title(query, limit=15)

    if not results:
        not_found_text = (
            f"❌ **No results found for:** `{query}`\n\n"
            f"💡 **Tips:**\n"
            f"• Check the spelling\n"
            f"• Try searching with fewer words (e.g. `Loki` instead of `Loki Season 2 Ep 3`)"
        )
        await message.answer(not_found_text, parse_mode="Markdown")
        return

    search_text = f"🔎 **Found {len(results)} result(s) for:** `{query}`\n\n_Please select from below:_"
    keyboard = search_results_keyboard(results)
    await message.answer(search_text, reply_markup=keyboard, parse_mode="Markdown")
