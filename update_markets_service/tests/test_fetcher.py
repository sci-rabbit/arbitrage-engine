"""Tests for GetFetcher.fetch_json."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientResponseError

from core.load_markets.fetcher import GetFetcher, RateLimitError


def _make_session(status: int, json_data=None):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.request_info = MagicMock()
    resp.history = ()
    resp.headers = {}

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get = MagicMock(return_value=cm)
    return session


# Patch asyncio.sleep so tenacity retries don't wait in tests
@pytest.fixture(autouse=True)
def instant_retry(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())


@pytest.mark.asyncio
async def test_status_200_returns_json():
    session = _make_session(200, {"key": "value"})
    fetcher = GetFetcher()
    result = await fetcher.fetch_json(session, "http://test/api")
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_status_500_retries_then_raises_client_response_error():
    session = _make_session(500)
    fetcher = GetFetcher()
    with pytest.raises(ClientResponseError):
        await fetcher.fetch_json(session, "http://test/api")
    # 5 attempts total (1 initial + 4 retries)
    assert session.get.call_count == 5


@pytest.mark.asyncio
async def test_status_429_retries_then_raises_rate_limit_error():
    session = _make_session(429)
    fetcher = GetFetcher()
    with pytest.raises(RateLimitError):
        await fetcher.fetch_json(session, "http://test/api")
    assert session.get.call_count == 5


@pytest.mark.asyncio
async def test_status_404_raises_immediately_without_retry():
    session = _make_session(404)
    fetcher = GetFetcher()
    with pytest.raises(Exception, match="http://test/api"):
        await fetcher.fetch_json(session, "http://test/api")
    assert session.get.call_count == 1


@pytest.mark.asyncio
async def test_status_401_raises_immediately_without_retry():
    session = _make_session(401)
    fetcher = GetFetcher()
    with pytest.raises(Exception, match="Auth error"):
        await fetcher.fetch_json(session, "http://test/api")
    assert session.get.call_count == 1


@pytest.mark.asyncio
async def test_status_403_raises_immediately_without_retry():
    session = _make_session(403)
    fetcher = GetFetcher()
    with pytest.raises(Exception, match="Auth error"):
        await fetcher.fetch_json(session, "http://test/api")
    assert session.get.call_count == 1


@pytest.mark.asyncio
async def test_status_200_passes_params_and_headers():
    session = _make_session(200, [])
    fetcher = GetFetcher()
    await fetcher.fetch_json(session, "http://test/api", params={"limit": 10}, headers={"Auth": "tok"})
    session.get.assert_called_once()
    call_kwargs = session.get.call_args
    assert call_kwargs[1]["params"] == {"limit": 10}
    assert call_kwargs[1]["headers"] == {"Auth": "tok"}