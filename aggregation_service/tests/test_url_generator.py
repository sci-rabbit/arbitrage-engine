"""Tests for generate_market_url utility."""
from core.utils.url_generator import generate_market_url


def test_polymarket_with_event_slug():
    url = generate_market_url("polymarket", "0xabc", event_slug="bitcoin-etf-2027")
    assert url == "https://polymarket.com/event/bitcoin-etf-2027"


def test_polymarket_without_slug_falls_back_to_market_id():
    url = generate_market_url("polymarket", "0xabc123")
    assert url == "https://polymarket.com/market/0xabc123"


def test_kalshi_with_series_and_event_id():
    url = generate_market_url("kalshi", "MKT-1", event_id="EVT-1", series_ticker="SERIES-X")
    assert url == "https://kalshi.com/markets/series-x/evt-1"


def test_kalshi_with_series_no_event_id():
    url = generate_market_url("kalshi", "MKT-1", series_ticker="SERIES-X")
    assert url == "https://kalshi.com/markets/series-x/mkt-1"


def test_kalshi_fallback_when_no_series():
    url = generate_market_url("kalshi", "MKT-1")
    assert url == "https://kalshi.com/trade/mkt-1"


def test_predict_fun_with_event_slug():
    url = generate_market_url("predict_fun", "some-id", event_slug="trump-2028")
    assert url == "https://predict.fun/market/trump-2028"


def test_predict_fun_without_slug_falls_back_to_market_id():
    url = generate_market_url("predict_fun", "some-id-123")
    assert url == "https://predict.fun/market/some-id-123"


def test_unknown_platform_returns_hash():
    url = generate_market_url("unknown_platform", "some-id")
    assert url == "#"
