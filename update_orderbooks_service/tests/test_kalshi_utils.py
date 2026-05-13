from core.kalshi_utils import dollars_fp_to_cents


def test_empty_input_returns_empty():
    assert dollars_fp_to_cents([]) == []
    assert dollars_fp_to_cents(None) == []


def test_converts_dollar_string_to_cents():
    result = dollars_fp_to_cents([["0.0100", "200.00"]])
    assert result == [[1, 200.0]]


def test_rounds_to_nearest_cent():
    # 0.005 * 100 = 0.5 → rounds to 1 (banker's or standard rounding via round())
    result = dollars_fp_to_cents([["0.005", "10"]])
    assert result[0][0] == int(round(0.005 * 100))


def test_multiple_entries():
    entries = [["0.10", "50"], ["0.90", "30"]]
    result = dollars_fp_to_cents(entries)
    assert result == [[10, 50.0], [90, 30.0]]


def test_skips_entries_too_short():
    result = dollars_fp_to_cents([["0.10"], []])
    assert result == []


def test_skips_non_list_entries():
    result = dollars_fp_to_cents([None, "bad", 42, ["0.50", "10"]])
    assert result == [[50, 10.0]]


def test_skips_unparseable_values():
    result = dollars_fp_to_cents([["abc", "10"], ["0.10", "xyz"]])
    # second entry has a parseable price but unparseable size → skipped
    assert result == []


def test_float_inputs_work():
    result = dollars_fp_to_cents([[0.5, 100.0]])
    assert result == [[50, 100.0]]
