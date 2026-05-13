"""Tests for fetch_series_ticker, load_kalshi_markets, load_polymarket_markets, load_predict_fun_markets."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.load_markets.loaders.load_kalshi import fetch_series_ticker, load_kalshi_markets
from core.load_markets.loaders.load_polymarket import load_polymarket_markets
from core.load_markets.loaders.load_predict_fun import load_predict_fun_markets


# ---------------------------------------------------------------------------
# fetch_series_ticker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_series_ticker_success():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(return_value={"event": {"series_ticker": "SER-1"}})

    with patch("core.load_markets.loaders.load_kalshi.settings") as mock_settings:
        mock_settings.kalshi.events_url = "http://api/events"
        result = await fetch_series_ticker("EVT-1", AsyncMock(), fetcher)

    assert result == ("EVT-1", "SER-1")


@pytest.mark.asyncio
async def test_fetch_series_ticker_missing_series_returns_none():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(return_value={"event": {}})

    with patch("core.load_markets.loaders.load_kalshi.settings") as mock_settings:
        mock_settings.kalshi.events_url = "http://api/events"
        result = await fetch_series_ticker("EVT-1", AsyncMock(), fetcher)

    assert result == ("EVT-1", None)


@pytest.mark.asyncio
async def test_fetch_series_ticker_exception_returns_none():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=Exception("Network error"))

    with patch("core.load_markets.loaders.load_kalshi.settings") as mock_settings:
        mock_settings.kalshi.events_url = "http://api/events"
        result = await fetch_series_ticker("EVT-X", AsyncMock(), fetcher)

    assert result == ("EVT-X", None)


# ---------------------------------------------------------------------------
# load_kalshi_markets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_kalshi_single_page():
    markets = [{"ticker": "T1"}, {"ticker": "T2"}]
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(return_value={"markets": markets, "cursor": None})

    batches = []
    async for batch in load_kalshi_markets(AsyncMock(), fetcher, limit=100, url="http://api"):
        batches.append(batch)

    assert batches == [markets]


@pytest.mark.asyncio
async def test_load_kalshi_multi_page_follows_cursor():
    page1 = [{"ticker": "T1"}]
    page2 = [{"ticker": "T2"}]
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=[
        {"markets": page1, "cursor": "cursor-1"},
        {"markets": page2, "cursor": None},
    ])

    batches = []
    async for batch in load_kalshi_markets(AsyncMock(), fetcher, limit=10, url="http://api"):
        batches.append(batch)

    assert batches == [page1, page2]


@pytest.mark.asyncio
async def test_load_kalshi_empty_response_stops():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(return_value={"markets": [], "cursor": None})

    batches = []
    async for batch in load_kalshi_markets(AsyncMock(), fetcher, limit=10, url="http://api"):
        batches.append(batch)

    assert batches == []


@pytest.mark.asyncio
async def test_load_kalshi_exception_stops_iteration():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=Exception("connection refused"))

    batches = []
    async for batch in load_kalshi_markets(AsyncMock(), fetcher, limit=10, url="http://api"):
        batches.append(batch)

    assert batches == []


# ---------------------------------------------------------------------------
# load_polymarket_markets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_polymarket_single_page():
    markets = [{"id": "1"}, {"id": "2"}]
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=[markets, []])

    batches = []
    async for batch in load_polymarket_markets(AsyncMock(), fetcher, limit=10, url="http://api"):
        batches.append(batch)

    assert batches == [markets]


@pytest.mark.asyncio
async def test_load_polymarket_advances_offset_between_pages():
    page1 = [{"id": "1"}]
    page2 = [{"id": "2"}]
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=[page1, page2, []])

    batches = []
    async for batch in load_polymarket_markets(AsyncMock(), fetcher, limit=5, url="http://api"):
        batches.append(batch)

    assert len(batches) == 2
    calls = fetcher.fetch_json.call_args_list
    assert calls[0][1]["params"]["offset"] == 0
    assert calls[1][1]["params"]["offset"] == 5
    assert calls[2][1]["params"]["offset"] == 10


@pytest.mark.asyncio
async def test_load_polymarket_empty_first_response_stops():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(return_value=[])

    batches = []
    async for batch in load_polymarket_markets(AsyncMock(), fetcher, limit=10, url="http://api"):
        batches.append(batch)

    assert batches == []


# ---------------------------------------------------------------------------
# load_predict_fun_markets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_predict_fun_dict_success_yields_data():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=[
        {"success": True, "data": [{"id": "1"}], "cursor": None},
        {"success": True, "data": [], "cursor": None},
    ])

    batches = []
    async for batch in load_predict_fun_markets(AsyncMock(), fetcher, url="http://api"):
        batches.append(batch)

    assert len(batches) == 1
    assert batches[0] == [{"id": "1"}]


@pytest.mark.asyncio
async def test_load_predict_fun_success_false_stops():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(return_value={"success": False, "error": "unauthorized"})

    batches = []
    async for batch in load_predict_fun_markets(AsyncMock(), fetcher, url="http://api"):
        batches.append(batch)

    assert batches == []


@pytest.mark.asyncio
async def test_load_predict_fun_list_response():
    markets = [{"id": "a"}, {"id": "b"}]
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=[markets, []])

    batches = []
    async for batch in load_predict_fun_markets(AsyncMock(), fetcher, url="http://api"):
        batches.append(batch)

    assert batches == [markets]


@pytest.mark.asyncio
async def test_load_predict_fun_cursor_pagination():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=[
        {"success": True, "data": [{"id": "1"}], "cursor": "c1"},
        {"success": True, "data": [{"id": "2"}], "cursor": None},
        {"success": True, "data": [], "cursor": None},
    ])

    batches = []
    async for batch in load_predict_fun_markets(AsyncMock(), fetcher, url="http://api"):
        batches.append(batch)

    assert len(batches) == 2
    calls = fetcher.fetch_json.call_args_list
    assert "after" not in (calls[0][1].get("params") or {})
    assert calls[1][1]["params"]["after"] == "c1"


@pytest.mark.asyncio
async def test_load_predict_fun_exception_stops():
    fetcher = MagicMock()
    fetcher.fetch_json = AsyncMock(side_effect=Exception("timeout"))

    batches = []
    async for batch in load_predict_fun_markets(AsyncMock(), fetcher, url="http://api"):
        batches.append(batch)

    assert batches == []