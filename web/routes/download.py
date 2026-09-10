import logging
import re
import urllib.parse
from typing import Optional, Tuple
from fastapi import APIRouter, Request, HTTPException, status, Header
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


def make_safe_content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Create a safe Content-Disposition header preventing header injection and handling UTF-8."""
    cleaned = re.sub(r'[\r\n\x00-\x1f\x7f"]', '_', filename or "video.mp4").strip()
    if not cleaned:
        cleaned = "video.mp4"
    ascii_safe = cleaned.encode("ascii", "replace").decode("ascii").replace("?", "_")
    encoded_utf8 = urllib.parse.quote(cleaned, encoding="utf-8")
    return f'{disposition}; filename="{ascii_safe}"; filename*=UTF-8\'\'{encoded_utf8}'


def parse_range_header(range_header: Optional[str], file_size: Optional[int]) -> Optional[Tuple[int, Optional[int]]]:
    """Parse and validate HTTP Range header (e.g. bytes=0-1023)."""
    if not range_header or not range_header.startswith("bytes="):
        return None
    try:
        range_val = range_header[6:].strip()
        parts = range_val.split("-")
        if len(parts) != 2:
            return None
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else None
        if start < 0 or (file_size and start >= file_size):
            return None
        if end is not None and file_size and end >= file_size:
            end = file_size - 1
        if end is not None and end < start:
            return None
        return (start, end)
    except Exception:
        return None


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
            request=request,
            name="download.html",
            context={
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
                request=request,
                name="download.html",
                context={
                    "error": "The requested media file was not found in the library database.",
                    "bot_username": "Webseries_hitt_bot",
                    "title": "File Not Found",
                },
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Cross-content relationship integrity check
        if file_obj.episode and file_obj.episode.season:
            if file_obj.episode.season.content_id != file_obj.content_id:
                logger.error(f"Integrity error: file {file_obj.id} episode content mismatch.")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted file relationship")

        # Build Title and Subtitle
        title = file_obj.content.title if file_obj.content else "Media"
        subtitle = None
        if file_obj.episode:
            season_num = file_obj.episode.season.season_number if file_obj.episode.season else 1
            ep_num = file_obj.episode.episode_number
            subtitle = f"Season {season_num} • Episode {ep_num}"
            if file_obj.episode.title and not file_obj.episode.title.lower().startswith("episode"):
                subtitle += f" - {file_obj.episode.title}"

        return templates.TemplateResponse(
            request=request,
            name="download.html",
            context={
                "file": file_obj,
                "title": title,
                "subtitle": subtitle,
                "token": token,
                "bot_username": "Webseries_hitt_bot",
                "error": None
            }
        )


@router.get("/stream/{token}")
async def stream_video_file(token: str, range: Optional[str] = Header(None)):
    """
    Direct MTProto video streaming endpoint for HTML5 player without saving video to VPS disk.
    Strictly uses file metadata from database and ignores client query params.
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

        # Cross-content relationship integrity check
        if file_obj.episode and file_obj.episode.season:
            if file_obj.episode.season.content_id != file_obj.content_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted file relationship")

        channel_id = file_obj.telegram_channel_id
        message_id = file_obj.telegram_message_id
        file_size = file_obj.file_size_bytes
        file_name = file_obj.file_name or "video.mp4"

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": make_safe_content_disposition(file_name, disposition="inline"),
    }

    range_bounds = parse_range_header(range, file_size)
    offset_bytes = range_bounds[0] if range_bounds else 0

    if file_size:
        if range_bounds:
            end_byte = range_bounds[1] if range_bounds[1] is not None else file_size - 1
            content_length = (end_byte - offset_bytes) + 1
            headers["Content-Range"] = f"bytes {offset_bytes}-{end_byte}/{file_size}"
            headers["Content-Length"] = str(content_length)
            status_code = status.HTTP_206_PARTIAL_CONTENT
        else:
            headers["Content-Length"] = str(file_size)
            status_code = status.HTTP_200_OK
    else:
        status_code = status.HTTP_200_OK

    media_generator = TelegramStreamer.stream_media_chunks(channel_id, message_id, offset_bytes=offset_bytes)
    return StreamingResponse(media_generator, status_code=status_code, media_type="video/mp4", headers=headers)


@router.get("/file/{token}")
async def download_direct_file(token: str):
    """
    Direct attachment download endpoint.
    Strictly uses database file identifiers and safe Content-Disposition headers.
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

        if file_obj.episode and file_obj.episode.season:
            if file_obj.episode.season.content_id != file_obj.content_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted file relationship")

        channel_id = file_obj.telegram_channel_id
        message_id = file_obj.telegram_message_id
        file_name = file_obj.file_name or "video.mp4"
        file_size = file_obj.file_size_bytes

    headers = {
        "Content-Disposition": make_safe_content_disposition(file_name, disposition="attachment"),
        "Accept-Ranges": "bytes",
    }
    if file_size:
        headers["Content-Length"] = str(file_size)

    media_generator = TelegramStreamer.stream_media_chunks(channel_id, message_id)
    return StreamingResponse(media_generator, media_type="application/octet-stream", headers=headers)
