"""Tests for the /markets API routes."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.markets import router
from core.models.database import get_ro_session, get_rw_session


def _make_app():
    app = FastAPI()
    app.include_router(router)
    session = AsyncMock()
    app.dependency_overrides[get_ro_session] = lambda: session
    app.dependency_overrides[get_rw_session] = lambda: session
    return app


def _market(platform="kalshi", mid="MKT-1", title="Will X?"):
    m = MagicMock()
    m.platform = platform
    m.platform_market_id = mid
    m.title = title
    m.description = None
    m.close_time = None
    return m


def _pair(final_score=0.85, distance=0.3):
    p = MagicMock()
    p.id = 1
    p.final_score = final_score
    p.distance = distance
    p.title_channel_score = 0.9
    p.semantic_channel_score = 0.8
    return p


def _orderbook(mid="MKT-1"):
    ob = MagicMock()
    ob.platform_market_id = mid
    ob.orderbook = {"yes": [], "no": []}
    ob.updated_at = datetime(2027, 1, 1)
    return ob


# ---------------------------------------------------------------------------
# GET /markets/platforms
# ---------------------------------------------------------------------------

def test_get_platforms_returns_list():
    app = _make_app()
    with patch("api.markets.MarketRepository") as MockRepo:
        MockRepo.return_value.get_platforms = AsyncMock(return_value=["kalshi", "polymarket"])
        with TestClient(app) as client:
            resp = client.get("/markets/platforms")
    assert resp.status_code == 200
    assert resp.json() == ["kalshi", "polymarket"]


def test_get_platforms_empty():
    app = _make_app()
    with patch("api.markets.MarketRepository") as MockRepo:
        MockRepo.return_value.get_platforms = AsyncMock(return_value=[])
        with TestClient(app) as client:
            resp = client.get("/markets/platforms")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /markets/add_pair
# ---------------------------------------------------------------------------

def test_add_pair_calls_repo():
    app = _make_app()
    with patch("api.markets.PairRepository") as MockRepo:
        MockRepo.return_value.add_pair = AsyncMock(return_value={"added": 1})
        with TestClient(app) as client:
            resp = client.post("/markets/add_pair", json=[["id1", "id2"]])
    assert resp.status_code == 200
    MockRepo.return_value.add_pair.assert_called_once_with(markets_ids_list=[["id1", "id2"]])


# ---------------------------------------------------------------------------
# DELETE /markets/delete
# ---------------------------------------------------------------------------

def test_delete_pair_calls_repo():
    app = _make_app()
    with patch("api.markets.PairRepository") as MockRepo:
        MockRepo.return_value.delete_pair = AsyncMock(return_value=None)
        with TestClient(app) as client:
            resp = client.request(
                "DELETE",
                "/markets/delete",
                content=json.dumps({"market_ids": ["id1", "id2"]}),
                headers={"Content-Type": "application/json"},
            )
    assert resp.status_code == 200
    MockRepo.return_value.delete_pair.assert_called_once_with(market_ids=["id1", "id2"])


# ---------------------------------------------------------------------------
# GET /markets/market/{common_id}
# ---------------------------------------------------------------------------

def test_find_market_returns_market_short_list():
    app = _make_app()
    market = _market(platform="kalshi", mid="MKT-1", title="Will X?")
    with patch("api.markets.MarketService") as MockSvc:
        MockSvc.return_value.search = AsyncMock(return_value=[market])
        with TestClient(app) as client:
            resp = client.get("/markets/market/MKT-1?platform=kalshi")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["platform"] == "kalshi"
    assert data[0]["platform_market_id"] == "MKT-1"
    assert data[0]["title"] == "Will X?"


def test_find_market_no_results_returns_empty_list():
    app = _make_app()
    with patch("api.markets.MarketService") as MockSvc:
        MockSvc.return_value.search = AsyncMock(return_value=[])
        with TestClient(app) as client:
            resp = client.get("/markets/market/UNKNOWN?platform=kalshi")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /markets/search
# ---------------------------------------------------------------------------

def test_search_returns_market_list():
    app = _make_app()
    market = _market(platform="polymarket", mid="0xabc", title="Will Y?")
    with patch("api.markets.MarketRepository") as MockRepo:
        MockRepo.return_value.search_by_query = AsyncMock(return_value=[market])
        with TestClient(app) as client:
            resp = client.get("/markets/search?text=bitcoin&platform=polymarket")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["platform"] == "polymarket"
    assert data[0]["platform_market_id"] == "0xabc"


def test_search_lowercases_query_text():
    app = _make_app()
    with patch("api.markets.MarketRepository") as MockRepo:
        MockRepo.return_value.search_by_query = AsyncMock(return_value=[])
        with TestClient(app) as client:
            client.get("/markets/search?text=BITCOIN&platform=kalshi")
        MockRepo.return_value.search_by_query.assert_called_once_with(
            text="bitcoin", platform="kalshi"
        )


# ---------------------------------------------------------------------------
# GET /markets/pairs
# ---------------------------------------------------------------------------

def test_get_pairs_returns_market_pairs():
    app = _make_app()
    pair = _pair()
    ma = _market(mid="A")
    mb = _market(mid="B")
    with patch("api.markets.PairRepository") as MockRepo:
        MockRepo.return_value.get_all_pairs_with_markets = AsyncMock(
            return_value=[(pair, [ma, mb])]
        )
        with TestClient(app) as client:
            resp = client.get("/markets/pairs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["market_a"]["platform_market_id"] == "A"
    assert data[0]["market_b"]["platform_market_id"] == "B"
    assert abs(data[0]["final_score"] - 0.85) < 1e-9
    assert data[0]["channels"]["title"] == 0.9


def test_get_pairs_skips_incomplete_pairs():
    app = _make_app()
    pair = _pair()
    ma = _market(mid="A")
    with patch("api.markets.PairRepository") as MockRepo:
        MockRepo.return_value.get_all_pairs_with_markets = AsyncMock(
            return_value=[(pair, [ma])]  # only 1 market → skip
        )
        with TestClient(app) as client:
            resp = client.get("/markets/pairs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_pairs_passes_query_params_to_repo():
    app = _make_app()
    with patch("api.markets.PairRepository") as MockRepo:
        MockRepo.return_value.get_all_pairs_with_markets = AsyncMock(return_value=[])
        with TestClient(app) as client:
            client.get("/markets/pairs?max_distance=0.6&final_score=0.8&limit=100&offset=50")
        MockRepo.return_value.get_all_pairs_with_markets.assert_called_once_with(
            threshold_distance=0.6,
            threshold_final_score=0.8,
            limit=100,
            offset=50,
        )


# ---------------------------------------------------------------------------
# GET /markets/orderbooks
# ---------------------------------------------------------------------------

def test_get_orderbooks_returns_list():
    app = _make_app()
    ob = _orderbook("MKT-1")
    with patch("api.markets.OrderbookRepository") as MockRepo:
        MockRepo.return_value.get_by_platform_market_ids = AsyncMock(return_value=[ob])
        with TestClient(app) as client:
            resp = client.get("/markets/orderbooks?platform_market_ids=MKT-1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["platform_market_id"] == "MKT-1"


def test_get_orderbooks_empty_when_none_found():
    app = _make_app()
    with patch("api.markets.OrderbookRepository") as MockRepo:
        MockRepo.return_value.get_by_platform_market_ids = AsyncMock(return_value=[])
        with TestClient(app) as client:
            resp = client.get("/markets/orderbooks?platform_market_ids=MISSING")
    assert resp.status_code == 200
    assert resp.json() == []