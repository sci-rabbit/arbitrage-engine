"""
Tests for _process_market filtering logic in all three loader services.

_process_market is the core decision function: save / delete / skip (None).
No DB or HTTP needed — we bypass __init__ and mock only what the method uses.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.kalshi_markets_loader import KalshiLoaderService
from services.polymarket_markets_loader import PolymarketLoaderService
from services.predict_fun_markets_loader import PredictFunLoaderService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future(days=30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _past(days=1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _existing_market(market_id="mkt-1"):
    return MagicMock(platform_market_id=market_id)


def make_kalshi():
    svc = KalshiLoaderService.__new__(KalshiLoaderService)
    svc.existing_markets_map = {}
    svc.semaphore = asyncio.Semaphore(1)
    svc.aio_session = AsyncMock()
    svc.fetcher = MagicMock()
    return svc


def make_poly():
    svc = PolymarketLoaderService.__new__(PolymarketLoaderService)
    svc.existing_markets_map = {}
    return svc


def make_pf():
    svc = PredictFunLoaderService.__new__(PredictFunLoaderService)
    svc.existing_markets_map = {}
    return svc


# ---------------------------------------------------------------------------
# KalshiLoaderService._process_market
# ---------------------------------------------------------------------------

KALSHI_VALID = {
    "ticker": "T1",
    "status": "open",
    "close_time": None,
    "volume_fp": "1000",
    "title": "Test",
    "event_ticker": None,
}


@pytest.mark.asyncio
async def test_kalshi_existing_inactive_returns_delete():
    svc = make_kalshi()
    svc.existing_markets_map = {"T1": _existing_market("T1")}
    result = await svc._process_market({**KALSHI_VALID, "status": "closed"})
    assert result == {"action": "delete", "market_id": "T1"}


@pytest.mark.asyncio
async def test_kalshi_existing_active_returns_none():
    svc = make_kalshi()
    svc.existing_markets_map = {"T1": _existing_market("T1")}
    result = await svc._process_market({**KALSHI_VALID, "status": "open"})
    assert result is None


@pytest.mark.asyncio
async def test_kalshi_non_active_status_skipped():
    svc = make_kalshi()
    result = await svc._process_market({**KALSHI_VALID, "status": "finalized"})
    assert result is None


@pytest.mark.asyncio
async def test_kalshi_expired_close_time_skipped():
    svc = make_kalshi()
    result = await svc._process_market({**KALSHI_VALID, "close_time": _past()})
    assert result is None


@pytest.mark.asyncio
async def test_kalshi_low_volume_skipped():
    svc = make_kalshi()
    result = await svc._process_market({**KALSHI_VALID, "volume_fp": "1"})
    assert result is None


@pytest.mark.asyncio
async def test_kalshi_valid_returns_save():
    svc = make_kalshi()
    with patch(
        "services.kalshi_markets_loader.fetch_series_ticker",
        new=AsyncMock(return_value=(None, None)),
    ):
        result = await svc._process_market(
            {**KALSHI_VALID, "close_time": _future(), "event_ticker": "EVT"}
        )
    assert result is not None
    assert result["action"] == "save"
    assert result["market"].platform == "kalshi"


@pytest.mark.asyncio
async def test_kalshi_series_ticker_injected_when_returned():
    svc = make_kalshi()
    raw = {**KALSHI_VALID, "close_time": _future(), "event_ticker": "EVT"}
    with patch(
        "services.kalshi_markets_loader.fetch_series_ticker",
        new=AsyncMock(return_value=(None, "SERIES-1")),
    ):
        result = await svc._process_market(raw)
    assert result["market"].series_ticker == "SERIES-1"


# ---------------------------------------------------------------------------
# PolymarketLoaderService._process_market
# ---------------------------------------------------------------------------

POLY_VALID = {
    "id": "1",
    "closed": False,
    "outcomePrices": ["0.60", "0.40"],
    "endDate": None,
    "volume": "1000",
}


def test_poly_existing_closed_returns_delete():
    svc = make_poly()
    svc.existing_markets_map = {"1": _existing_market("1")}
    result = svc._process_market({**POLY_VALID, "closed": True})
    assert result == {"action": "delete", "market_id": "1"}


def test_poly_existing_open_returns_none():
    svc = make_poly()
    svc.existing_markets_map = {"1": _existing_market("1")}
    result = svc._process_market({**POLY_VALID, "closed": False})
    assert result is None


def test_poly_closed_new_market_skipped():
    svc = make_poly()
    result = svc._process_market({**POLY_VALID, "closed": True})
    assert result is None


def test_poly_low_yes_price_skipped():
    svc = make_poly()
    result = svc._process_market({**POLY_VALID, "outcomePrices": ["0.005", "0.995"]})
    assert result is None


def test_poly_low_no_price_skipped():
    svc = make_poly()
    result = svc._process_market({**POLY_VALID, "outcomePrices": ["0.995", "0.005"]})
    assert result is None


def test_poly_expired_end_date_skipped():
    svc = make_poly()
    result = svc._process_market({**POLY_VALID, "endDate": _past()})
    assert result is None


def test_poly_low_volume_skipped():
    svc = make_poly()
    result = svc._process_market({**POLY_VALID, "volume": "1"})
    assert result is None


def test_poly_valid_returns_save():
    svc = make_poly()
    result = svc._process_market({**POLY_VALID, "endDate": _future()})
    assert result is not None
    assert result["action"] == "save"
    assert result["market"].platform == "polymarket"


# ---------------------------------------------------------------------------
# PredictFunLoaderService._process_market
# ---------------------------------------------------------------------------

PF_VALID = {"id": "42", "status": "OPEN"}


def test_pf_existing_resolved_returns_delete():
    svc = make_pf()
    svc.existing_markets_map = {"42": _existing_market("42")}
    result = svc._process_market({**PF_VALID, "status": "RESOLVED"})
    assert result == {"action": "delete", "market_id": "42"}


def test_pf_existing_active_returns_none():
    svc = make_pf()
    svc.existing_markets_map = {"42": _existing_market("42")}
    result = svc._process_market({**PF_VALID, "status": "OPEN"})
    assert result is None


def test_pf_invalid_status_skipped():
    svc = make_pf()
    result = svc._process_market({**PF_VALID, "status": "UNKNOWN"})
    assert result is None


def test_pf_open_returns_save():
    svc = make_pf()
    result = svc._process_market({**PF_VALID, "status": "OPEN"})
    assert result is not None
    assert result["action"] == "save"
    assert result["market"].platform == "predict_fun"


def test_pf_registered_returns_save():
    svc = make_pf()
    result = svc._process_market({**PF_VALID, "status": "REGISTERED"})
    assert result["action"] == "save"


def test_pf_status_case_insensitive():
    svc = make_pf()
    result = svc._process_market({**PF_VALID, "status": "open"})
    assert result["action"] == "save"