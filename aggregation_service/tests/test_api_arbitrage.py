"""Tests for the /arbitrage API routes."""
import orjson
from unittest.mock import AsyncMock, MagicMock, patch

import redis.exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.arbitrage import router
from api.deps import require_access
from core.models.database import get_ro_session


def _make_app():
    app = FastAPI()
    app.include_router(router)
    session = AsyncMock()
    app.dependency_overrides[get_ro_session] = lambda: session
    app.dependency_overrides[require_access] = lambda: None
    return app


def _market(mid="MKT-1", platform="kalshi"):
    m = MagicMock()
    m.platform = platform
    m.platform_market_id = mid
    m.title = "Will X?"
    m.description = None
    m.close_time = None
    m.event_slug = None
    m.event_id = None
    m.series_ticker = None
    return m


def _pair():
    p = MagicMock()
    p.id = 1
    p.final_score = 0.9
    p.distance = 0.2
    return p


def _orderbook(mid="MKT-1"):
    ob = MagicMock()
    ob.platform_market_id = mid
    ob.orderbook = {"yes": [[0.6, 100]], "no": [[0.35, 100]]}
    return ob


def _opportunity():
    return {
        "direction": "YES_YES",
        "entry_price_1": 0.6,
        "entry_price_2": 0.35,
        "entry_spread": 0.05,
        "min_size_per_market": 25.0,
        "min_spread": 0.04,
        "avg_sum_at_min_spread": 0.96,
        "pnl_at_min_spread": 0.04,
        "max_spread": 0.1,
        "avg_sum_at_max_spread": 0.9,
        "pnl_at_max_spread": 0.1,
        "final_contracts": 25.0,
        "final_cost": 24.0,
        "final_avg_price": 0.96,
        "final_spread": 0.05,
        "final_pnl": 1.25,
    }


# ---------------------------------------------------------------------------
# GET /arbitrage/scan
# ---------------------------------------------------------------------------

def test_scan_returns_empty_when_no_pairs():
    app = _make_app()
    with patch("api.arbitrage.PairRepository") as MockPair:
        MockPair.return_value.get_all_pairs_with_markets = AsyncMock(return_value=[])
        with TestClient(app) as client:
            resp = client.get("/arbitrage/scan")
    assert resp.status_code == 200
    assert resp.json() == []


def test_scan_skips_pair_with_missing_orderbook():
    app = _make_app()
    pair = _pair()
    ma = _market("A")
    mb = _market("B")
    with patch("api.arbitrage.PairRepository") as MockPair, \
         patch("api.arbitrage.OrderbookRepository") as MockOB:
        MockPair.return_value.get_all_pairs_with_markets = AsyncMock(
            return_value=[(pair, [ma, mb])]
        )
        MockOB.return_value.get_by_platform_market_ids = AsyncMock(return_value=[])
        with TestClient(app) as client:
            resp = client.get("/arbitrage/scan")
    assert resp.status_code == 200
    assert resp.json() == []


def test_scan_returns_opportunities():
    app = _make_app()
    pair = _pair()
    ma = _market("A")
    mb = _market("B")
    ob_a = _orderbook("A")
    ob_b = _orderbook("B")
    opp = _opportunity()
    with patch("api.arbitrage.PairRepository") as MockPair, \
         patch("api.arbitrage.OrderbookRepository") as MockOB, \
         patch("api.arbitrage.check_arbitrage", return_value=[opp]):
        MockPair.return_value.get_all_pairs_with_markets = AsyncMock(
            return_value=[(pair, [ma, mb])]
        )
        MockOB.return_value.get_by_platform_market_ids = AsyncMock(
            return_value=[ob_a, ob_b]
        )
        with TestClient(app) as client:
            resp = client.get("/arbitrage/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["market_a"]["platform_market_id"] == "A"
    assert data[0]["market_b"]["platform_market_id"] == "B"
    assert len(data[0]["arbitrage"]) == 1
    assert data[0]["arbitrage"][0]["direction"] == "YES_YES"


def test_scan_skips_pair_on_check_arbitrage_exception():
    app = _make_app()
    pair = _pair()
    ma = _market("A")
    mb = _market("B")
    ob_a = _orderbook("A")
    ob_b = _orderbook("B")
    with patch("api.arbitrage.PairRepository") as MockPair, \
         patch("api.arbitrage.OrderbookRepository") as MockOB, \
         patch("api.arbitrage.check_arbitrage", side_effect=ValueError("bad data")):
        MockPair.return_value.get_all_pairs_with_markets = AsyncMock(
            return_value=[(pair, [ma, mb])]
        )
        MockOB.return_value.get_by_platform_market_ids = AsyncMock(
            return_value=[ob_a, ob_b]
        )
        with TestClient(app) as client:
            resp = client.get("/arbitrage/scan")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /arbitrage/scan_cache
# ---------------------------------------------------------------------------

def test_scan_cache_returns_empty_on_cache_miss():
    app = _make_app()
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    app.state.redis_service = redis_mock
    with TestClient(app) as client:
        resp = client.get("/arbitrage/scan_cache")
    assert resp.status_code == 200
    assert resp.json() == []


def test_scan_cache_returns_parsed_cached_data():
    app = _make_app()
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=orjson.dumps([]))
    app.state.redis_service = redis_mock
    with TestClient(app) as client:
        resp = client.get("/arbitrage/scan_cache")
    assert resp.status_code == 200
    assert resp.json() == []


def test_scan_cache_returns_empty_on_redis_connection_error():
    app = _make_app()
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(side_effect=redis.exceptions.ConnectionError("down"))
    app.state.redis_service = redis_mock
    with TestClient(app) as client:
        resp = client.get("/arbitrage/scan_cache")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /arbitrage/compute
# ---------------------------------------------------------------------------

def test_compute_returns_empty_when_orderbooks_missing():
    app = _make_app()
    with patch("api.arbitrage.OrderbookRepository") as MockOB:
        MockOB.return_value.get_by_platform_market_ids = AsyncMock(return_value=[])
        with TestClient(app) as client:
            resp = client.get("/arbitrage/compute?platform_market_id_a=A&platform_market_id_b=B")
    assert resp.status_code == 200
    assert resp.json() == []


def test_compute_returns_opportunities():
    app = _make_app()
    ob_a = _orderbook("A")
    ob_b = _orderbook("B")
    opp = _opportunity()
    with patch("api.arbitrage.OrderbookRepository") as MockOB, \
         patch("api.arbitrage.check_arbitrage", return_value=[opp]):
        MockOB.return_value.get_by_platform_market_ids = AsyncMock(
            return_value=[ob_a, ob_b]
        )
        with TestClient(app) as client:
            resp = client.get("/arbitrage/compute?platform_market_id_a=A&platform_market_id_b=B")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["direction"] == "YES_YES"
    assert abs(data[0]["entry_price_1"] - 0.6) < 1e-9


def test_compute_returns_empty_when_one_orderbook_has_null_data():
    app = _make_app()
    ob_a = MagicMock()
    ob_a.platform_market_id = "A"
    ob_a.orderbook = None  # null orderbook
    ob_b = _orderbook("B")
    with patch("api.arbitrage.OrderbookRepository") as MockOB:
        MockOB.return_value.get_by_platform_market_ids = AsyncMock(
            return_value=[ob_a, ob_b]
        )
        with TestClient(app) as client:
            resp = client.get("/arbitrage/compute?platform_market_id_a=A&platform_market_id_b=B")
    assert resp.status_code == 200
    assert resp.json() == []