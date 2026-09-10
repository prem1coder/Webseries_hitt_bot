from bot.handlers.start import router as start_router
from bot.handlers.search import router as search_router
from bot.handlers.callbacks import router as callbacks_router

__all__ = ["start_router", "search_router", "callbacks_router"]
