"""Tests for submitter retry logic."""

import httpx
import pytest
import respx

from pramana.submitter import _post_single

SUBMIT_URL = "https://test.pramana.dev/api/submit"
HEADERS = {"Content-Type": "application/json"}
PAYLOAD = {"model_id": "gpt-4.1", "prompt_id": "test-001", "output": "hello"}


@pytest.fixture
def mock_api():
    with respx.mock:
        yield respx.post(SUBMIT_URL)


@pytest.mark.asyncio
async def test_post_single_success(mock_api):
    """Successful POST returns response body."""
    mock_api.return_value = httpx.Response(200, json={"status": "submitted"})

    async with httpx.AsyncClient() as client:
        result = await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert result == {"status": "submitted"}
    assert mock_api.call_count == 1


@pytest.mark.asyncio
async def test_post_single_retries_on_connect_error(mock_api):
    """Transient ConnectError triggers retry, succeeds on second attempt."""
    mock_api.side_effect = [
        httpx.ConnectError("DNS resolution failed"),
        httpx.Response(200, json={"status": "submitted"}),
    ]

    async with httpx.AsyncClient() as client:
        result = await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert result == {"status": "submitted"}
    assert mock_api.call_count == 2


@pytest.mark.asyncio
async def test_post_single_retries_on_os_error(mock_api):
    """OSError (Errno 8 DNS failure) triggers retry."""
    mock_api.side_effect = [
        OSError(8, "nodename nor servname provided, or not known"),
        httpx.Response(200, json={"status": "submitted"}),
    ]

    async with httpx.AsyncClient() as client:
        result = await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert result == {"status": "submitted"}
    assert mock_api.call_count == 2


@pytest.mark.asyncio
async def test_post_single_retries_on_timeout(mock_api):
    """ReadTimeout triggers retry."""
    mock_api.side_effect = [
        httpx.ReadTimeout("Read timed out"),
        httpx.Response(200, json={"status": "submitted"}),
    ]

    async with httpx.AsyncClient() as client:
        result = await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert result == {"status": "submitted"}
    assert mock_api.call_count == 2


@pytest.mark.asyncio
async def test_post_single_retries_on_429(mock_api):
    """Rate limit (429) triggers retry with Retry-After header."""
    mock_api.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json={"status": "submitted"}),
    ]

    async with httpx.AsyncClient() as client:
        result = await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert result == {"status": "submitted"}
    assert mock_api.call_count == 2


@pytest.mark.asyncio
async def test_post_single_raises_after_max_retries(mock_api):
    """Persistent transient errors exhaust retries and propagate."""
    mock_api.side_effect = httpx.ConnectError("DNS resolution failed")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ConnectError):
            await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    # 1 initial + 5 retries = 6
    assert mock_api.call_count == 6


@pytest.mark.asyncio
async def test_post_single_422_no_retry(mock_api):
    """422 errors are not retried — they indicate bad payload."""
    mock_api.return_value = httpx.Response(
        422, json={"detail": "invalid prompt_id"},
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError, match="422"):
            await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert mock_api.call_count == 1


@pytest.mark.asyncio
async def test_post_single_500_no_retry(mock_api):
    """Server errors (500) are not retried — only transient network errors are."""
    mock_api.return_value = httpx.Response(500)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):
            await _post_single(client, SUBMIT_URL, PAYLOAD, HEADERS)

    assert mock_api.call_count == 1
