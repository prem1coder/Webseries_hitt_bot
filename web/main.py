import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database.config import get_settings
from database.connection import init_db
from web.routes import download_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("web")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI Web Server starting...")
    await init_db()
    yield
    logger.info("FastAPI Web Server stopped.")


app = FastAPI(
    title="Webseries Hitt Download Portal",
    description="Secure streaming and download portal for Webseries Hitt Bot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Routes
app.include_router(download_router)


if __name__ == "__main__":
    uvicorn.run(
        "web.main:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=False
    )
