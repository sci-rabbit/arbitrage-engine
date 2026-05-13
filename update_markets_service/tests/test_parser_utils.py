"""Tests for pure utility functions: parse_dt, string_to_json, get_float."""
from datetime import datetime, timezone

from core.market_parsers.utils import parse_dt, string_to_json
from core.load_markets.converters import get_float


# ---------------------------------------------------------------------------
# parse_dt
# ---------------------------------------------------------------------------

def test_parse_dt_none_returns_none():
    assert parse_dt(None) is None


def test_parse_dt_empty_string_returns_none():
    assert parse_dt("") is None


def test_parse_dt_valid_iso_returns_datetime():
    result = parse_dt("2025-06-15T12:00:00+00:00")
    assert isinstance(result, datetime)
    assert result.year == 2025
    assert result.month == 6


def test_parse_dt_z_suffix_converted():
    result = parse_dt("2025-01-01T00:00:00Z")
    assert result is not None
    assert result.tzinfo is not None


def test_parse_dt_invalid_string_returns_none():
    assert parse_dt("not-a-date") is None
    assert parse_dt("2025-13-01") is None


# ---------------------------------------------------------------------------
# string_to_json
# ---------------------------------------------------------------------------

def test_string_to_json_parses_json_string():
    result = string_to_json('["Yes", "No"]', "test")
    assert result == ["Yes", "No"]


def test_string_to_json_passes_dict_through():
    data = {"key": "value"}
    assert string_to_json(data, "test") is data


def test_string_to_json_passes_list_through():
    data = ["Yes", "No"]
    assert string_to_json(data, "test") is data


def test_string_to_json_invalid_json_returns_none():
    result = string_to_json("{bad json}", "test")
    assert result is None


# ---------------------------------------------------------------------------
# get_float
# ---------------------------------------------------------------------------

def test_get_float_converts_number():
    assert get_float(1000) == 1000.0
    assert get_float("250.5") == 250.5


def test_get_float_returns_zero_for_none():
    assert get_float(None) == 0


def test_get_float_returns_zero_for_invalid():
    assert get_float("abc") == 0
    assert get_float([]) == 0