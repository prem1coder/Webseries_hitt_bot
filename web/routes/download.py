import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from database.config import get_settings
from database.connection import get_db_session
from database.repositories.file_repo import FileRepository
from web.services.token_service import TokenService
from web.services.telegram_streamer import TelegramStreamer

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="web/templates")
settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "webseries_hitt_download_portal"}


@router.get("/download/{token}", response_class=HTMLResponse)
async def view_download_page(request: Request, token: str):
    """
    Validate download token and render the responsive download / player portal.
    """
    payload = TokenService.verify_download_token(token)
    if not payload:
        return templates.TemplateResponse(
            "download.html",
            {
                "request": request,
                "error": "This download link is invalid or has expired. Please search again in the Telegram bot to get a fresh link.",
                "bot_username": "Webseries_hitt_bot",
                "title": "Link Expired",
            },
            status_code=status.HTTP_410_GONE
        )

    file_id = payload.get("fid")

    async with get_db_session() as session:
        file_repo = FileRepository(session)
        file_obj = await file_repo.get_by_id(file_id)

        if not file_obj:
            return templates.TemplateResponse(
                "download.html",
                {
                    "request": request,
                    "error": "The requested media file was not found in the library database.",
                    "bot_username": "Webseries_hitt_bot",
                    "title": "File Not Found",
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Build Title and Subtitle
        title = file_obj.content.title
        subtitle = None
        if file_obj.episode:
            season_num = file_obj.episode.season.season_number if file_obj.episode.season else 1
            ep_num = file_obj.episode.episode_number
            subtitle = f"Season {season_num} • Episode {ep_num}"
            if file_obj.episode.title and not file_obj.episode.title.lower().startswith("episode"):
                subtitle += f" - {file_obj.episode.title}"

        return templates.TemplateResponse(
            "download.html",
            {
                "request": request,
                "file": file_obj,
                "title": title,
                "subtitle": subtitle,
                "token": token,
                "bot_username": "Webseries_hitt_bot",
                "error": None
            }
        )


@router.get("/stream/{token}")
async def stream_video_file(token: str):
    """
    Direct MTProto video streaming endpoint for HTML5 player without saving video to VPS disk.
    """
    payload = TokenService.verify_download_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token invalid or expired")

    file_id = payload.get("fid")

    async with get_db_session() as session:
        file_repo = FileRepository(session)
        file_obj = await file_repo.get_by_id(file_id)

        if not file_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        channel_id = file_obj.telegram_channel_id
        message_id = file_obj.telegram_message_id
        file_size = file_obj.file_size_bytes

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{file_obj.file_name}"',
    }
    if file_size:
        headers["Content-Length"] = str(file_size)

    media_generator = TelegramStreamer.stream_media_chunks(channel_id, message_id)
    return StreamingResponse(media_generator, media_type="video/mp4", headers=headers)


@router.get("/file/{token}")
async def download_direct_file(token: str):
    """
    Direct attachment download endpoint.
    """
    payload = TokenService.verify_download_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token invalid or expired")

    file_id = payload.get("fid")

    async with get_db_session() as session:
        file_repo = FileRepository(session)
        file_obj = await file_repo.get_by_id(file_id)

        if not file_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        channel_id = file_obj.telegram_channel_id
        message_id = file_obj.telegram_message_id
        file_name = file_obj.file_name or "video.mp4"
        file_size = file_obj.file_size_bytes

    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Accept-Ranges": "bytes",
    }
    if file_size:
        headers["Content-Length"] = str(file_size)

    media_generator = TelegramStreamer.stream_media_chunks(channel_id, message_id)
    return StreamingResponse(media_generator, media_type="application/octet-stream", headers=headers)
