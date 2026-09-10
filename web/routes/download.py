import logging
import os
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


def get_safe_media_type(filename: str) -> str:
    """Derive safe MIME type from trusted extension; fallback to application/octet-stream."""
    _, ext = os.path.splitext((filename or "").lower())
    mime_map = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".m4v": "video/x-m4v",
        ".ts": "video/mp2t",
    }
    return mime_map.get(ext, "application/octet-stream")


def process_range_header(
    range_header: Optional[str],
    file_size: Optional[int]
) -> Tuple[int, Optional[int], Optional[str], int]:
    """
    Parse and validate HTTP Range header (RFC 7233 / RFC 9110).
    Returns (offset_bytes, end_byte, content_range_header_value, status_code).
    Raises HTTPException(416) for unsatisfiable or malformed requests.
    """
    if not range_header or not range_header.startswith("bytes="):
        return 0, (file_size - 1) if file_size else None, None, status.HTTP_200_OK

    range_spec = range_header[6:].strip()

    # Reject multi-range requests per V1 specification
    if "," in range_spec:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Multi-range requests are not supported",
            headers={"Content-Range": f"bytes */{file_size if file_size else '*'}"}
        )

    if "-" not in range_spec:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Malformed range specification",
            headers={"Content-Range": f"bytes */{file_size if file_size else '*'}"}
        )

    if not file_size or file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Range unsatisfiable for unknown or empty file size",
            headers={"Content-Range": "bytes */*"}
        )

    parts = range_spec.split("-", 1)
    raw_start, raw_end = parts[0].strip(), parts[1].strip()

    # Suffix range: bytes=-500
    if not raw_start and raw_end:
        if not raw_end.isdigit():
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Invalid suffix range",
                headers={"Content-Range": f"bytes */{file_size}"}
            )
        suffix_len = int(raw_end)
        if suffix_len <= 0:
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Suffix length must be positive",
                headers={"Content-Range": f"bytes */{file_size}"}
            )
        start = max(0, file_size - suffix_len)
        end = file_size - 1

    # Open-ended range: bytes=100-
    elif raw_start and not raw_end:
        if not raw_start.isdigit():
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Invalid start range",
                headers={"Content-Range": f"bytes */{file_size}"}
            )
        start = int(raw_start)
        if start >= file_size:
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Range start exceeds file size",
                headers={"Content-Range": f"bytes */{file_size}"}
            )
        end = file_size - 1

    # Closed range: bytes=100-200
    elif raw_start and raw_end:
        if not raw_start.isdigit() or not raw_end.isdigit():
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Non-numeric range bounds",
                headers={"Content-Range": f"bytes */{file_size}"}
            )
        start = int(raw_start)
        end = int(raw_end)
        if start >= file_size or start > end:
            raise HTTPException(
                status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
                detail="Range start invalid or exceeds file size",
                headers={"Content-Range": f"bytes */{file_size}"}
            )
        if end >= file_size:
            end = file_size - 1
    else:
        # bytes=-
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="Empty range bounds",
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    content_range = f"bytes {start}-{end}/{file_size}"
    return start, end, content_range, status.HTTP_206_PARTIAL_CONTENT


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
    Strictly uses file metadata from database and derives safe MIME types.
    Protected by concurrency limits.
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

    media_type = get_safe_media_type(file_name)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": make_safe_content_disposition(file_name, disposition="inline"),
    }

    offset_bytes, end_byte, content_range, status_code = process_range_header(range, file_size)

    if file_size and end_byte is not None:
        content_length = (end_byte - offset_bytes) + 1
        headers["Content-Length"] = str(content_length)
        if content_range:
            headers["Content-Range"] = content_range

    media_generator = TelegramStreamer.stream_media_chunks(channel_id, message_id, offset_bytes=offset_bytes)
    return StreamingResponse(media_generator, status_code=status_code, media_type=media_type, headers=headers)


@router.get("/file/{token}")
async def download_direct_file(token: str, range: Optional[str] = Header(None)):
    """
    Direct attachment download endpoint with consistent HTTP Range processing.
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

    offset_bytes, end_byte, content_range, status_code = process_range_header(range, file_size)

    if file_size and end_byte is not None:
        content_length = (end_byte - offset_bytes) + 1
        headers["Content-Length"] = str(content_length)
        if content_range:
            headers["Content-Range"] = content_range

    media_generator = TelegramStreamer.stream_media_chunks(channel_id, message_id, offset_bytes=offset_bytes)
    return StreamingResponse(media_generator, status_code=status_code, media_type="application/octet-stream", headers=headers)
