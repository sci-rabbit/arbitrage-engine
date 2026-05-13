"""Tests for temporal parsing and similarity."""
from datetime import datetime

from core.similarity.temporal.client import get_temporal_similarity, temporal_similarity
from core.similarity.temporal.parser import parse_temporal

# ---------------------------------------------------------------------------
# parse_temporal
# ---------------------------------------------------------------------------

def test_parse_temporal_in_year():
    start, end = parse_temporal("Will X happen in 2027?")
    assert start is not None and start.year == 2027
    assert end is not None and end.year == 2027


def test_parse_temporal_no_date_returns_none_none():
    assert parse_temporal("Will anything happen?") == (None, None)


def test_parse_temporal_price_like_filtered():
    # Texts with decimal numbers like "150.00" are filtered out
    assert parse_temporal("price above 150.00") == (None, None)


def test_parse_temporal_before_month_year():
    _, end = parse_temporal("Will this happen before March 2028?")
    assert end is not None and end.year == 2028 and end.month == 3


def test_parse_temporal_by_month_year():
    _, end = parse_temporal("Will it be done by June 2029?")
    assert end is not None and end.year == 2029


def test_parse_temporal_year_below_min_year_returns_none():
    # MIN_YEAR = 2026, so years below that are ignored
    result = parse_temporal("Will it happen in 2024?")
    assert result == (None, None)


# ---------------------------------------------------------------------------
# temporal_similarity
# ---------------------------------------------------------------------------

def test_temporal_similarity_same_end_dates():
    d = datetime(2027, 6, 15)
    assert temporal_similarity((None, d), (None, d)) == 1.0


def test_temporal_similarity_one_day_apart():
    d1 = datetime(2027, 6, 15)
    d2 = datetime(2027, 6, 16)
    assert temporal_similarity((None, d1), (None, d2)) == 1.0


def test_temporal_similarity_two_days_apart():
    d1 = datetime(2027, 6, 15)
    d2 = datetime(2027, 6, 17)
    assert temporal_similarity((None, d1), (None, d2)) == 0.0


def test_temporal_similarity_large_gap():
    d1 = datetime(2027, 1, 1)
    d2 = datetime(2028, 1, 1)
    assert temporal_similarity((None, d1), (None, d2)) == 0.0


# ---------------------------------------------------------------------------
# get_temporal_similarity
# ---------------------------------------------------------------------------

def test_get_temporal_similarity_same_year_returns_one():
    result = get_temporal_similarity("Will X happen in 2027?", "Will Y happen in 2027?")
    assert result["temporal"] == 1.0


def test_get_temporal_similarity_different_years_returns_zero():
    result = get_temporal_similarity("Will X happen in 2027?", "Will Y happen in 2028?")
    assert result["temporal"] == 0.0


def test_get_temporal_similarity_returns_interval_fields():
    result = get_temporal_similarity("Will X happen in 2027?", "Will Y happen in 2027?")
    assert "interval_a" in result
    assert "interval_b" in result
    assert "temporal" in result


def test_get_temporal_similarity_no_dates_returns_one():
    # Both have (None, None) → today used as end for both → delta=0 → 1.0
    result = get_temporal_similarity("Will anything happen?", "Will something occur?")
    assert result["temporal"] == 1.0
