"""Tests for normalize_prices and should_skip_market."""
from core.load_markets.loaders.utils import normalize_prices, should_skip_market

# ---------------------------------------------------------------------------
# normalize_prices
# ---------------------------------------------------------------------------

def test_normalize_prices_kalshi_style():
    m = {"yes_bid": "0.45", "yes_ask": "0.50", "no_bid": "0.45", "no_ask": "0.50"}
    p = normalize_prices(m)
    assert p == {"yes_bid": 0.45, "yes_ask": 0.50, "no_bid": 0.45, "no_ask": 0.50}


def test_normalize_prices_kalshi_none_values():
    m = {"yes_bid": None, "yes_ask": "0.50", "no_bid": None, "no_ask": "0.50"}
    p = normalize_prices(m)
    assert p["yes_bid"] is None
    assert p["no_bid"] is None
    assert p["yes_ask"] == 0.50


def test_normalize_prices_polymarket_style():
    m = {"outcomePrices": ["0.65", "0.35"]}
    p = normalize_prices(m)
    assert p == {"yes_bid": 0.65, "yes_ask": 0.65, "no_bid": 0.35, "no_ask": 0.35}


def test_normalize_prices_fallback_all_none():
    p = normalize_prices({})
    assert all(v is None for v in p.values())


# ---------------------------------------------------------------------------
# should_skip_market
# ---------------------------------------------------------------------------

def _poly(yes, no):
    return {"outcomePrices": [str(yes), str(no)]}


def _kalshi(yb, ya, nb, na):
    return {"yes_bid": yb, "yes_ask": ya, "no_bid": nb, "no_ask": na}


def test_skip_when_all_prices_none():
    assert should_skip_market({}) is True


def test_skip_when_price_out_of_range_high():
    assert should_skip_market(_poly(1.5, -0.5)) is True


def test_skip_when_price_negative():
    assert should_skip_market(_poly(-0.1, 1.1)) is True


def test_skip_when_both_bids_zero():
    # polymarket: bid == ask, so yes_bid=0 and no_bid=0
    assert should_skip_market(_poly(0.0, 0.0)) is True


def test_skip_when_prob_sum_too_low():
    # ya + na = 0.50 + 0.40 = 0.90 < 0.97
    m = _kalshi(yb=0.48, ya=0.50, nb=0.38, na=0.40)
    assert should_skip_market(m) is True


def test_skip_when_prob_sum_too_high():
    # ya + na = 0.60 + 0.60 = 1.20 > 1.03
    m = _kalshi(yb=0.55, ya=0.60, nb=0.55, na=0.60)
    assert should_skip_market(m) is True


def test_skip_when_yes_bid_near_resolved():
    m = _kalshi(yb=0.99, ya=0.995, nb=0.003, na=0.005)
    assert should_skip_market(m) is True


def test_skip_when_no_bid_near_resolved():
    m = _kalshi(yb=0.003, ya=0.005, nb=0.99, na=0.995)
    assert should_skip_market(m) is True


def test_skip_when_yes_ask_too_low():
    m = _kalshi(yb=0.005, ya=0.01, nb=0.98, na=0.99)
    assert should_skip_market(m) is True


def test_skip_when_no_ask_too_low():
    m = _kalshi(yb=0.98, ya=0.99, nb=0.005, na=0.01)
    assert should_skip_market(m) is True


def test_skip_when_broken_kalshi_orderbook():
    # yes_bid > yes_ask — invalid spread
    m = _kalshi(yb=0.55, ya=0.45, nb=0.45, na=0.55)
    assert should_skip_market(m) is True


def test_valid_kalshi_market_not_skipped():
    m = _kalshi(yb=0.45, ya=0.50, nb=0.45, na=0.50)
    assert should_skip_market(m) is False


def test_valid_polymarket_not_skipped():
    # outcomePrices sum ≈ 1.0, above min thresholds
    assert should_skip_market(_poly(0.60, 0.40)) is False


def test_valid_polymarket_near_even_not_skipped():
    assert should_skip_market(_poly(0.50, 0.50)) is False
