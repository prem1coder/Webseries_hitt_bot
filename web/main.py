import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database.config import get_settings
from database.connection import check_db_ready, dispose_engine
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
    settings.validate_for_environment()
    try:
        await check_db_ready()
        logger.info("Database schema and connectivity verified.")
    except Exception as e:
        logger.critical(f"Database readiness check failed: {e}. Refusing to start web server.")
        raise RuntimeError(f"Database readiness check failed: {e}") from e
    yield
    logger.info("Disposing database engine on shutdown...")
    await dispose_engine()
    logger.info("FastAPI Web Server stopped.")


app = FastAPI(
    title="Webseries Hitt Download Portal",
    description="Secure streaming and download portal for Webseries Hitt Bot",
    version="1.0.0",
    lifespan=lifespan
)

# Restrict CORS to configured domain and localhost
allowed_origins = [
    settings.base_web_url,
    f"http://localhost:{settings.WEB_PORT}",
    f"http://127.0.0.1:{settings.WEB_PORT}",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
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
