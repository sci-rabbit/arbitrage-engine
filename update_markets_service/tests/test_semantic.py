"""Tests for build_semantic_text."""
from unittest.mock import MagicMock

from core.market_parsers.semantic import build_semantic_text


def _market(**kwargs):
    m = MagicMock()
    m.title = kwargs.get("title", "")
    m.description = kwargs.get("description", "")
    m.raw = kwargs.get("raw", {})
    return m


def test_only_title():
    m = _market(title="Will X happen?", description="", raw={})
    assert build_semantic_text(m) == "Will X happen?"


def test_title_and_description():
    m = _market(title="T", description="D", raw={})
    assert build_semantic_text(m) == "T\nD"


def test_empty_title_not_included():
    m = _market(title="", description="D", raw={})
    assert build_semantic_text(m) == "D"


def test_kalshi_rules_primary_and_secondary():
    m = _market(title="T", description="", raw={"rules_primary": "Rule A", "rules_secondary": "Rule B"})
    text = build_semantic_text(m)
    assert "Rule A" in text
    assert "Rule B" in text


def test_polymarket_event_description():
    m = _market(title="T", description="", raw={"events": [{"description": "Event desc"}]})
    text = build_semantic_text(m)
    assert "Event desc" in text


def test_empty_events_list_ignored():
    m = _market(title="T", description="", raw={"events": []})
    assert build_semantic_text(m) == "T"


def test_event_without_description_ignored():
    m = _market(title="T", description="", raw={"events": [{"slug": "no-desc"}]})
    assert build_semantic_text(m) == "T"


def test_all_parts_combined():
    m = _market(
        title="T",
        description="D",
        raw={
            "rules_primary": "RP",
            "rules_secondary": "RS",
            "events": [{"description": "ED"}],
        },
    )
    text = build_semantic_text(m)
    assert text == "T\nD\nRP\nRS\nED"


def test_raw_none_treated_as_empty():
    m = _market(title="T", description="D")
    m.raw = None
    assert build_semantic_text(m) == "T\nD"