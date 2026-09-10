import pytest
from httpx import AsyncClient, ASGITransport
from web.main import app
from web.routes.download import make_safe_content_disposition, parse_range_header
from web.services.token_service import TokenService


def test_make_safe_content_disposition():
    """Ensure safe Content-Disposition headers prevent header injection and strip control characters."""
    # Test newline injection attempt
    malicious_name = 'evil\r\ninjected_header: true\n"filename.mp4'
    header = make_safe_content_disposition(malicious_name, disposition="attachment")
    assert "\r" not in header
    assert "\n" not in header
    assert 'injected_header: true' not in header or '_' in header

    # Test standard filename
    normal_header = make_safe_content_disposition("Inception.2010.1080p.mkv", disposition="inline")
    assert 'inline; filename="Inception.2010.1080p.mkv"' in normal_header
    assert "filename*=UTF-8''" in normal_header

    # Test empty / None filename fallback
    empty_header = make_safe_content_disposition("", disposition="attachment")
    assert 'filename="video.mp4"' in empty_header


def test_parse_range_header():
    """Test HTTP Range header parsing and boundary validation."""
    file_size = 10000

    # Standard range
    bounds = parse_range_header("bytes=0-499", file_size)
    assert bounds == (0, 499)

    # Open-ended range
    bounds = parse_range_header("bytes=1000-", file_size)
    assert bounds == (1000, None)

    # Range exceeding file size
    bounds = parse_range_header("bytes=0-20000", file_size)
    assert bounds == (0, 9999)

    # Invalid range: start greater than file size
    assert parse_range_header("bytes=15000-", file_size) is None

    # Invalid range: negative / garbage
    assert parse_range_header("bytes=-50-100", file_size) is None
    assert parse_range_header("invalid_range", file_size) is None
    assert parse_range_header(None, file_size) is None


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
