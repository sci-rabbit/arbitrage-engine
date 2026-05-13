"""Tests for KalshiParser, PolyMarketParser, PredictFunParser."""
from datetime import datetime, timezone

from core.market_parsers.kalshi_parser import KalshiParser
from core.market_parsers.polymarket_parser import PolyMarketParser
from core.market_parsers.predict_fun_parser import PredictFunParser, _date_from_slug


# ---------------------------------------------------------------------------
# KalshiParser
# ---------------------------------------------------------------------------

def _kalshi_raw(**kwargs):
    base = {
        "ticker": "KXTEST-25",
        "event_ticker": "KXTEST",
        "title": "Will X happen?",
        "yes_sub_title": "Yes",
        "no_sub_title": "No",
        "category": "politics",
        "rules_primary": "Primary rule",
        "rules_secondary": "",
        "open_time": "2025-01-01T00:00:00Z",
        "close_time": "2025-12-31T23:59:59Z",
        "liquidity": "5000.0",
        "volume_24h": "1200.0",
    }
    base.update(kwargs)
    return base


def test_kalshi_platform():
    assert KalshiParser.parse_market(_kalshi_raw())["platform"] == "kalshi"


def test_kalshi_unwraps_market_key():
    wrapped = {"market": _kalshi_raw()}
    result = KalshiParser.parse_market(wrapped)
    assert result["platform_market_id"] == "KXTEST-25"


def test_kalshi_direct_dict():
    result = KalshiParser.parse_market(_kalshi_raw())
    assert result["platform_market_id"] == "KXTEST-25"
    assert result["event_id"] == "KXTEST"


def test_kalshi_outcomes_binary():
    result = KalshiParser.parse_market(_kalshi_raw())
    assert result["outcomes"]["type"] == "binary"
    assert result["outcomes"]["labels"] == ["Yes", "No"]


def test_kalshi_outcomes_defaults_when_missing():
    raw = _kalshi_raw()
    del raw["yes_sub_title"]
    del raw["no_sub_title"]
    result = KalshiParser.parse_market(raw)
    assert result["outcomes"]["labels"] == ["Yes", "No"]


def test_kalshi_description_combines_rules():
    raw = _kalshi_raw(rules_primary="Primary.", rules_secondary="Secondary.")
    result = KalshiParser.parse_market(raw)
    desc = result["description"].lower()
    assert "primary." in desc
    assert "secondary." in desc


def test_kalshi_liquidity_and_volume_as_float():
    result = KalshiParser.parse_market(_kalshi_raw())
    assert isinstance(result["liquidity"], float)
    assert isinstance(result["volume_24h"], float)


def test_kalshi_none_liquidity_stays_none():
    raw = _kalshi_raw(liquidity=None, volume_24h=None)
    result = KalshiParser.parse_market(raw)
    assert result["liquidity"] is None
    assert result["volume_24h"] is None


def test_kalshi_title_normalized():
    result = KalshiParser.parse_market(_kalshi_raw(title="Will X Happen?"))
    assert result["normalized_title"] == "will x happen?"


# ---------------------------------------------------------------------------
# PolyMarketParser
# ---------------------------------------------------------------------------

def _poly_raw(**kwargs):
    base = {
        "id": "123",
        "question": "Will Y happen?",
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["tok1", "tok2"]',
        "category": "sports",
        "description": "A market description",
        "liquidityNum": "10000",
        "volume24hr": "500",
        "startDate": "2025-01-01T00:00:00Z",
        "endDate": "2025-12-31T23:59:59Z",
        "gameStartTime": None,
        "events": [{"id": "evt-1", "slug": "event-slug"}],
    }
    base.update(kwargs)
    return base


def test_poly_platform():
    assert PolyMarketParser.parse_market(_poly_raw())["platform"] == "polymarket"


def test_poly_title_from_question():
    result = PolyMarketParser.parse_market(_poly_raw(question="My Question?"))
    assert result["title"] == "My Question?"
    assert result["normalized_title"] == "my question?"


def test_poly_is_binary_when_two_outcomes():
    result = PolyMarketParser.parse_market(_poly_raw())
    assert result["is_binary"] is True


def test_poly_is_not_binary_when_one_outcome():
    result = PolyMarketParser.parse_market(_poly_raw(outcomes='["Only"]'))
    assert result["is_binary"] is False


def test_poly_close_time_from_game_start():
    result = PolyMarketParser.parse_market(
        _poly_raw(gameStartTime="2025-06-01T18:00:00Z", endDate="2025-12-31T00:00:00Z")
    )
    assert result["close_time"].month == 6


def test_poly_close_time_falls_back_to_end_date():
    result = PolyMarketParser.parse_market(_poly_raw(gameStartTime=None))
    assert result["close_time"] is not None
    assert result["close_time"].year == 2025


def test_poly_event_id_from_events():
    result = PolyMarketParser.parse_market(_poly_raw())
    assert result["event_id"] == "evt-1"
    assert result["event_slug"] == "event-slug"


def test_poly_event_id_none_when_empty_events():
    result = PolyMarketParser.parse_market(_poly_raw(events=[]))
    assert result["event_id"] is None
    assert result["event_slug"] is None


# ---------------------------------------------------------------------------
# PredictFunParser + _date_from_slug
# ---------------------------------------------------------------------------

def test_date_from_slug_extracts_date():
    dt = _date_from_slug("nfl-game-2025-11-15")
    assert dt == datetime(2025, 11, 15, tzinfo=timezone.utc)


def test_date_from_slug_no_match_returns_none():
    assert _date_from_slug("no-date-here") is None
    assert _date_from_slug(None) is None


def _pf_raw(**kwargs):
    base = {
        "id": "42",
        "question": "Will team A win?",
        "createdAt": "2025-01-01T00:00:00Z",
        "categorySlug": "sports-2025-06-15",
        "conditionId": "cond-1",
        "description": "A description",
        "outcomes": [
            {"name": "Yes"},
            {"name": "No"},
        ],
    }
    base.update(kwargs)
    return base


def test_pf_platform():
    assert PredictFunParser.parse_market(_pf_raw())["platform"] == "predict_fun"


def test_pf_title_from_question():
    result = PredictFunParser.parse_market(_pf_raw(question="Big match?"))
    assert result["title"] == "Big match?"


def test_pf_title_falls_back_to_title_field():
    raw = _pf_raw()
    del raw["question"]
    raw["title"] = "Fallback title"
    result = PredictFunParser.parse_market(raw)
    assert result["title"] == "Fallback title"


def test_pf_binary_outcomes():
    result = PredictFunParser.parse_market(_pf_raw())
    assert result["outcomes"]["type"] == "binary"
    assert result["outcomes"]["labels"] == ["Yes", "No"]
    assert result["is_binary"] is True


def test_pf_multiple_outcomes():
    raw = _pf_raw(outcomes=[{"name": "A"}, {"name": "B"}, {"name": "C"}])
    result = PredictFunParser.parse_market(raw)
    assert result["outcomes"]["type"] == "multiple"
    assert result["is_binary"] is False


def test_pf_sports_close_time_from_slug():
    raw = _pf_raw(
        categorySlug="football-2025-09-20",
        outcomes=[{"name": "TeamA", "team": "TeamA"}, {"name": "TeamB", "team": "TeamB"}],
    )
    result = PredictFunParser.parse_market(raw)
    assert result["close_time"] == datetime(2025, 9, 20, tzinfo=timezone.utc)


def test_pf_non_sports_close_time_is_none():
    raw = _pf_raw(
        categorySlug="politics-2025-09-20",
        outcomes=[{"name": "Yes"}, {"name": "No"}],  # no "team" key
    )
    result = PredictFunParser.parse_market(raw)
    assert result["close_time"] is None