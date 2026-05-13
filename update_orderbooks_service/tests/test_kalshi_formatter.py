import pytest

from core.orderbook_formatters.kalshi_formatter import (
    format_kalshi_orderbook,
    _normalize_book,
    _convert_bids_to_asks,
)


# ---------------------------------------------------------------------------
# _normalize_book
# ---------------------------------------------------------------------------

def test_normalize_book_empty():
    assert _normalize_book([]) == []
    assert _normalize_book(None) == []


def test_normalize_book_converts_cents_to_decimal():
    result = _normalize_book([[50, 100]])
    assert result == [{"price": "0.50", "size": "100"}]


def test_normalize_book_sorted_best_bid_first():
    result = _normalize_book([[30, 10], [70, 20], [50, 15]])
    prices = [float(e["price"]) for e in result]
    assert prices == sorted(prices, reverse=True)


def test_normalize_book_skips_bad_entries():
    entries = [
        None,
        "bad",
        [50],          # too short
        [50, 10, 99],  # extra item — still valid
        [50, 10],
    ]
    result = _normalize_book(entries)
    prices = {e["price"] for e in result}
    assert "0.50" in prices
    assert len(result) == 2  # [50,10,99] and [50,10] both valid


# ---------------------------------------------------------------------------
# _convert_bids_to_asks
# ---------------------------------------------------------------------------

def test_convert_bids_to_asks_price_complement():
    bids = [{"price": "0.60", "size": "200"}]
    asks = _convert_bids_to_asks(bids)
    assert len(asks) == 1
    assert float(asks[0]["price"]) == pytest.approx(0.40, abs=1e-9)
    assert asks[0]["size"] == "200"


def test_convert_bids_to_asks_sorted_lowest_first():
    bids = [{"price": "0.70", "size": "1"}, {"price": "0.30", "size": "2"}]
    asks = _convert_bids_to_asks(bids)
    prices = [float(e["price"]) for e in asks]
    assert prices == sorted(prices)


# ---------------------------------------------------------------------------
# format_kalshi_orderbook — integration
# ---------------------------------------------------------------------------

def test_format_empty_response():
    result = format_kalshi_orderbook({})
    assert result["yes"]["bids"] == []
    assert result["yes"]["asks"] == []
    assert result["no"]["bids"] == []
    assert result["no"]["asks"] == []


def test_format_yes_asks_derived_from_no_bids():
    api = {"orderbook": {"yes": [[60, 100]], "no": [[40, 50]]}}
    result = format_kalshi_orderbook(api)
    # yes_asks = 1 - no_bids_price = 1 - 0.40 = 0.60
    yes_ask_price = float(result["yes"]["asks"][0]["price"])
    no_bid_price = float(result["no"]["bids"][0]["price"])
    assert yes_ask_price == pytest.approx(1.0 - no_bid_price, abs=1e-9)


def test_format_no_asks_derived_from_yes_bids():
    api = {"orderbook": {"yes": [[70, 30]], "no": [[30, 20]]}}
    result = format_kalshi_orderbook(api)
    no_ask_price = float(result["no"]["asks"][0]["price"])
    yes_bid_price = float(result["yes"]["bids"][0]["price"])
    assert no_ask_price == pytest.approx(1.0 - yes_bid_price, abs=1e-9)

