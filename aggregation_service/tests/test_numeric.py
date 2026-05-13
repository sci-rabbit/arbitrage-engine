"""Tests for numeric constraint parsing and conflict/match detection."""
from core.similarity.numeric.conflict import numeric_conflict, operators_conflict
from core.similarity.numeric.models import NumericConstraint, Operator
from core.similarity.numeric.pasrer import numeric_context_match, parse_numeric_constraints


def _c(op: Operator, val: float) -> NumericConstraint:
    return NumericConstraint(value=val, operator=op, span_text="")


# ---------------------------------------------------------------------------
# operators_conflict
# ---------------------------------------------------------------------------

def test_gt_vs_lt_conflict_when_gt_value_gte_lt_value():
    # "above 100" vs "below 80": 100 >= 80 → conflict
    assert operators_conflict(_c(Operator.GTE, 100), _c(Operator.LTE, 80)) is True


def test_gt_vs_lt_no_conflict_when_gt_value_lt_lt_value():
    # "above 50" vs "below 100": 50 < 100 → no conflict
    assert operators_conflict(_c(Operator.GTE, 50), _c(Operator.LTE, 100)) is False


def test_lt_vs_gt_conflict_symmetric():
    assert operators_conflict(_c(Operator.LTE, 80), _c(Operator.GTE, 100)) is True


def test_both_eq_same_value_no_conflict():
    assert operators_conflict(_c(Operator.EQ, 5), _c(Operator.EQ, 5)) is False


def test_both_eq_different_values_conflict():
    assert operators_conflict(_c(Operator.EQ, 5), _c(Operator.EQ, 6)) is True


def test_same_direction_same_value_no_conflict():
    assert operators_conflict(_c(Operator.GTE, 100), _c(Operator.GTE, 100)) is False


def test_same_direction_different_values_conflict():
    # GTE 100 vs GTE 150 — default tolerance=0.0 → conflict
    assert operators_conflict(_c(Operator.GTE, 100), _c(Operator.GTE, 150)) is True


def test_year_vs_non_year_eq_no_conflict():
    # year and non-year EQ values don't conflict (different semantic types)
    assert operators_conflict(_c(Operator.EQ, 2027), _c(Operator.EQ, 5)) is False


# ---------------------------------------------------------------------------
# numeric_conflict (list-level)
# ---------------------------------------------------------------------------

def test_numeric_conflict_detects_any():
    a = [_c(Operator.GTE, 100)]
    b = [_c(Operator.LTE, 80)]
    assert numeric_conflict(a, b) is True


def test_numeric_conflict_none_in_empty_lists():
    assert numeric_conflict([], []) is False


def test_numeric_conflict_no_conflict_same_direction():
    a = [_c(Operator.GTE, 50)]
    b = [_c(Operator.GTE, 50)]
    assert numeric_conflict(a, b) is False


def test_numeric_conflict_one_side_empty():
    assert numeric_conflict([_c(Operator.EQ, 5)], []) is False
    assert numeric_conflict([], [_c(Operator.EQ, 5)]) is False


# ---------------------------------------------------------------------------
# parse_numeric_constraints
# ---------------------------------------------------------------------------

def test_parse_above_100():
    result = parse_numeric_constraints("Will it go above 100?")
    ops = [c.operator for c in result]
    assert Operator.GTE in ops or Operator.GT in ops
    values = [c.value for c in result]
    assert 100.0 in values


def test_parse_below_50():
    result = parse_numeric_constraints("Will it fall below 50?")
    ops = [c.operator for c in result]
    assert Operator.LTE in ops or Operator.LT in ops


def test_parse_no_constraints_on_plain_text():
    result = parse_numeric_constraints("Will this event happen at all?")
    assert isinstance(result, list)


def test_parse_thousands_suffix():
    result = parse_numeric_constraints("Will it surpass 1k?")
    values = [c.value for c in result]
    assert any(abs(v - 1000.0) < 1e-3 for v in values)


def test_parse_millions_suffix():
    result = parse_numeric_constraints("above 2m revenue?")
    values = [c.value for c in result]
    assert any(abs(v - 2_000_000.0) < 1 for v in values)


def test_parse_percentage():
    result = parse_numeric_constraints("Will inflation reach above 3%?")
    assert len(result) > 0


# ---------------------------------------------------------------------------
# numeric_context_match
# ---------------------------------------------------------------------------

def test_context_match_same_gt():
    a = [_c(Operator.GTE, 100)]
    b = [_c(Operator.GTE, 100)]
    assert numeric_context_match(a, b) is True


def test_context_match_same_lt():
    a = [_c(Operator.LTE, 50)]
    b = [_c(Operator.LTE, 50)]
    assert numeric_context_match(a, b) is True


def test_context_match_different_operators_no_match():
    a = [_c(Operator.GTE, 100)]
    b = [_c(Operator.LTE, 100)]
    assert numeric_context_match(a, b) is False


def test_context_match_eq_same_value():
    a = [_c(Operator.EQ, 7)]
    b = [_c(Operator.EQ, 7)]
    assert numeric_context_match(a, b) is True


def test_context_match_eq_different_value():
    a = [_c(Operator.EQ, 7)]
    b = [_c(Operator.EQ, 8)]
    assert numeric_context_match(a, b) is False
