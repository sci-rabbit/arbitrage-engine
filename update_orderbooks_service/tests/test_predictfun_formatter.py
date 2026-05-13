from core.orderbook_formatters.predictfun_formatter import format_predictfun_orderbook


def _make_response(bids=None, asks=None, success=True):
    return {
        "success": success,
        "data": {
            "marketId": 1,
            "bids": bids or [],
            "asks": asks or [],
        },
    }


# ---------------------------------------------------------------------------
# Guard conditions
# ---------------------------------------------------------------------------

def test_returns_none_when_success_false():
    assert format_predictfun_orderbook({"success": False, "data": {}}) is None


def test_returns_none_when_no_data():
    assert format_predictfun_orderbook({"success": True}) is None
    assert format_predictfun_orderbook({"success": True, "data": {}}) is None


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_result_has_yes_no_keys():
    result = format_predictfun_orderbook(_make_response())
    assert "yes" in result
    assert "no" in result
    assert "bids" in result["yes"] and "asks" in result["yes"]
    assert "bids" in result["no"] and "asks" in result["no"]


def test_empty_bids_asks_produce_empty_lists():
    result = format_predictfun_orderbook(_make_response())
    assert result["yes"]["bids"] == []
    assert result["yes"]["asks"] == []
    assert result["no"]["bids"] == []
    assert result["no"]["asks"] == []


# ---------------------------------------------------------------------------
# Price symmetry: no_asks = 1 - yes_bids, no_bids = 1 - yes_asks
# ---------------------------------------------------------------------------

def test_no_asks_are_complement_of_yes_bids():
    resp = _make_response(bids=[[0.6, 100]])
    result = format_predictfun_orderbook(resp)
    yes_bid_price = float(result["yes"]["bids"][0]["price"])
    no_ask_price = float(result["no"]["asks"][0]["price"])
    assert abs(no_ask_price - (1.0 - yes_bid_price)) < 1e-6


def test_no_bids_are_complement_of_yes_asks():
    resp = _make_response(asks=[[0.7, 50]])
    result = format_predictfun_orderbook(resp)
    yes_ask_price = float(result["yes"]["asks"][0]["price"])
    no_bid_price = float(result["no"]["bids"][0]["price"])
    assert abs(no_bid_price - (1.0 - yes_ask_price)) < 1e-6


def test_bad_entries_skipped():
    resp = _make_response(bids=[None, "bad", [0.5], [0.5, 10]])
    result = format_predictfun_orderbook(resp)
    assert len(result["yes"]["bids"]) == 1
