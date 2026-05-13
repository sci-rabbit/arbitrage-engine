"""Tests for arbitrage pure functions: normalize_asks, cheapest_ask, calc_depth_arbitrage, check_arbitrage."""
import pytest
from services.arbitrage import normalize_asks, cheapest_ask, calc_depth_arbitrage, check_arbitrage


# ---------------------------------------------------------------------------
# normalize_asks
# ---------------------------------------------------------------------------

def test_normalize_asks_dict_format():
    asks = [{"price": "0.45", "size": "100"}, {"price": "0.50", "size": "50"}]
    result = normalize_asks(asks)
    assert result == [{"price": 0.45, "size": 100.0}, {"price": 0.50, "size": 50.0}]


def test_normalize_asks_list_format():
    asks = [["0.45", "100"], ["0.50", "50"]]
    result = normalize_asks(asks)
    assert result == [{"price": 0.45, "size": 100.0}, {"price": 0.50, "size": 50.0}]


def test_normalize_asks_sorted_ascending_by_price():
    asks = [{"price": "0.60", "size": "10"}, {"price": "0.40", "size": "20"}]
    result = normalize_asks(asks)
    assert result[0]["price"] < result[1]["price"]


def test_normalize_asks_empty():
    assert normalize_asks([]) == []


# ---------------------------------------------------------------------------
# cheapest_ask
# ---------------------------------------------------------------------------

def test_cheapest_ask_skips_levels_below_min_size():
    asks = [{"price": 0.40, "size": 10.0}, {"price": 0.45, "size": 100.0}]
    result = cheapest_ask(asks, min_size=50)
    assert result == {"price": 0.45, "size": 100.0}


def test_cheapest_ask_returns_first_if_all_meet_size():
    asks = [{"price": 0.40, "size": 100.0}, {"price": 0.45, "size": 100.0}]
    result = cheapest_ask(asks, min_size=25)
    assert result["price"] == 0.40


def test_cheapest_ask_none_when_no_level_meets_min_size():
    asks = [{"price": 0.40, "size": 10.0}, {"price": 0.45, "size": 20.0}]
    assert cheapest_ask(asks, min_size=50) is None


def test_cheapest_ask_empty():
    assert cheapest_ask([], min_size=10) is None


# ---------------------------------------------------------------------------
# calc_depth_arbitrage
# ---------------------------------------------------------------------------

def test_calc_depth_arbitrage_profitable():
    asks1 = [{"price": 0.45, "size": 100.0}]
    asks2 = [{"price": 0.45, "size": 100.0}]
    result = calc_depth_arbitrage(asks1, asks2, price_threshold=0.97)
    assert result is not None
    assert result["final_pnl"] > 0


def test_calc_depth_arbitrage_sum_above_threshold_returns_none():
    asks1 = [{"price": 0.55, "size": 100.0}]
    asks2 = [{"price": 0.55, "size": 100.0}]
    # 0.55 + 0.55 = 1.10 > 0.97 → no trades possible
    result = calc_depth_arbitrage(asks1, asks2, price_threshold=0.97)
    assert result is None


def test_calc_depth_arbitrage_empty_asks_returns_none():
    assert calc_depth_arbitrage([], [{"price": 0.45, "size": 100}], 0.97) is None
    assert calc_depth_arbitrage([{"price": 0.45, "size": 100}], [], 0.97) is None


def test_calc_depth_arbitrage_result_has_expected_keys():
    asks1 = [{"price": 0.40, "size": 200.0}]
    asks2 = [{"price": 0.40, "size": 200.0}]
    result = calc_depth_arbitrage(asks1, asks2, price_threshold=0.97)
    assert result is not None
    for key in ("max_spread", "final_contracts", "final_pnl", "final_spread"):
        assert key in result


def test_calc_depth_arbitrage_max_spread_floor():
    # raw spread 0.01 < MIN_MAX_SPREAD (0.03) → floor applied
    asks1 = [{"price": 0.495, "size": 100.0}]
    asks2 = [{"price": 0.495, "size": 100.0}]
    result = calc_depth_arbitrage(asks1, asks2, price_threshold=0.97)
    if result:
        assert result["max_spread"] >= 0.03


# ---------------------------------------------------------------------------
# check_arbitrage
# ---------------------------------------------------------------------------

def _ob(yes_ask_price, no_ask_price, size=100):
    return {
        "yes": {"asks": [{"price": yes_ask_price, "size": size}]},
        "no": {"asks": [{"price": no_ask_price, "size": size}]},
    }


def test_check_arbitrage_finds_opportunity():
    ob1 = _ob(0.45, 0.45)
    ob2 = _ob(0.45, 0.45)
    results = check_arbitrage(ob1, ob2)
    assert len(results) > 0


def test_check_arbitrage_no_opportunity_when_sum_too_high():
    ob1 = _ob(0.55, 0.55)
    ob2 = _ob(0.55, 0.55)
    results = check_arbitrage(ob1, ob2)
    assert results == []


def test_check_arbitrage_invalid_structure_returns_empty():
    ob_bad = {"bad": "structure"}
    ob_good = _ob(0.45, 0.45)
    assert check_arbitrage(ob_bad, ob_good) == []
    assert check_arbitrage(ob_good, ob_bad) == []


def test_check_arbitrage_missing_side_returns_empty():
    ob_incomplete = {"yes": {"asks": [{"price": 0.45, "size": 100}]}}
    ob_good = _ob(0.45, 0.45)
    assert check_arbitrage(ob_incomplete, ob_good) == []


def test_check_arbitrage_sorted_by_pnl_descending():
    ob1 = _ob(0.40, 0.40, size=500)
    ob2 = _ob(0.40, 0.40, size=500)
    results = check_arbitrage(ob1, ob2)
    if len(results) >= 2:
        assert results[0]["final_pnl"] >= results[1]["final_pnl"]


def test_check_arbitrage_direction_field_present():
    ob1 = _ob(0.45, 0.45)
    ob2 = _ob(0.45, 0.45)
    results = check_arbitrage(ob1, ob2)
    for r in results:
        assert "direction" in r
        assert r["direction"] in ("YES + NO", "NO + YES")