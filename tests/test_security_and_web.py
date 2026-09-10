import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from web.main import app
from web.routes.download import (
    make_safe_content_disposition,
    process_range_header,
    get_safe_media_type,
)
from web.services.token_service import TokenService


def test_make_safe_content_disposition():
    """Ensure safe Content-Disposition headers prevent header injection and strip control characters."""
    # Test newline injection attempt
    malicious_name = 'evil\r\ninjected_header: true\n"filename.mp4'
    header = make_safe_content_disposition(malicious_name, disposition="attachment")
    assert "\r" not in header
    assert "\n" not in header
    assert "injected_header" not in header or "_" in header

    # Test standard filename
    normal_header = make_safe_content_disposition("Inception.2010.1080p.mkv", disposition="inline")
    assert 'inline; filename="Inception.2010.1080p.mkv"' in normal_header
    assert "filename*=UTF-8''" in normal_header

    # Test empty / None filename fallback
    empty_header = make_safe_content_disposition("", disposition="attachment")
    assert 'filename="video.mp4"' in empty_header


def test_get_safe_media_type():
    """Verify MIME type resolution is derived safely from extension and never trusts user input."""
    assert get_safe_media_type("video.mp4") == "video/mp4"
    assert get_safe_media_type("movie.mkv") == "video/x-matroska"
    assert get_safe_media_type("stream.webm") == "video/webm"
    assert get_safe_media_type("clip.avi") == "video/x-msvideo"
    assert get_safe_media_type("film.mov") == "video/quicktime"
    assert get_safe_media_type("archive.zip") == "application/octet-stream"
    assert get_safe_media_type("unknown") == "application/octet-stream"


def test_process_range_header_valid_ranges():
    """Test HTTP Range header valid slices: closed, open-ended, and suffix ranges."""
    file_size = 10000

    # Closed range: bytes=0-499
    start, end, cr, code = process_range_header("bytes=0-499", file_size)
    assert (start, end, code) == (0, 499, 206)
    assert cr == "bytes 0-499/10000"

    # Open-ended range: bytes=1000-
    start, end, cr, code = process_range_header("bytes=1000-", file_size)
    assert (start, end, code) == (1000, 9999, 206)
    assert cr == "bytes 1000-9999/10000"

    # Suffix range: bytes=-500 (last 500 bytes)
    start, end, cr, code = process_range_header("bytes=-500", file_size)
    assert (start, end, code) == (9500, 9999, 206)
    assert cr == "bytes 9500-9999/10000"

    # Oversized end: bytes=0-20000 capped to file_size - 1
    start, end, cr, code = process_range_header("bytes=0-20000", file_size)
    assert (start, end, code) == (0, 9999, 206)
    assert cr == "bytes 0-9999/10000"

    # No Range header -> 200 OK
    start, end, cr, code = process_range_header(None, file_size)
    assert code == 200
    assert cr is None


def test_process_range_header_416_rejections():
    """Verify unsatisfiable and malformed ranges return HTTP 416 with Content-Range."""
    file_size = 10000

    # Multi-range rejected with 416
    with pytest.raises(HTTPException) as exc:
        process_range_header("bytes=0-100,200-300", file_size)
    assert exc.value.status_code == 416
    assert exc.value.headers.get("Content-Range") == f"bytes */{file_size}"

    # Start exceeds file size -> 416
    with pytest.raises(HTTPException) as exc:
        process_range_header("bytes=15000-", file_size)
    assert exc.value.status_code == 416
    assert exc.value.headers.get("Content-Range") == f"bytes */{file_size}"

    # Start > end -> 416
    with pytest.raises(HTTPException) as exc:
        process_range_header("bytes=500-200", file_size)
    assert exc.value.status_code == 416

    # Empty range -> 416
    with pytest.raises(HTTPException) as exc:
        process_range_header("bytes=-", file_size)
    assert exc.value.status_code == 416

    # Non-numeric range -> 416
    with pytest.raises(HTTPException) as exc:
        process_range_header("bytes=abc-def", file_size)
    assert exc.value.status_code == 416


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify health check endpoint returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_web_stream_and_download_endpoints_deny_invalid_token():
    """Verify stream and download endpoints reject expired, forged, or malformed tokens with 403/410."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid tokens should be rejected
        stream_resp = await client.get("/stream/invalid_fake_token")
        assert stream_resp.status_code == 403

        file_resp = await client.get("/file/invalid_fake_token")
        assert file_resp.status_code == 403

        page_resp = await client.get("/download/invalid_fake_token")
        assert page_resp.status_code == 410
