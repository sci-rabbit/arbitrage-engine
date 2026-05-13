"""
Tests for KalshiWSService._apply_snapshot and _apply_delta.

Both methods are pure in-memory state transitions on self.books_cents —
no DB, no network needed.
"""

from orderbook_service.kalshi.ws_service import KalshiWSService


def make_service() -> KalshiWSService:
    svc = KalshiWSService.__new__(KalshiWSService)
    svc.books_cents = {}
    return svc


# ---------------------------------------------------------------------------
# _apply_snapshot
# ---------------------------------------------------------------------------

def test_snapshot_stores_book():
    svc = make_service()
    svc._apply_snapshot("TICKER", [[60, 100.0], [50, 200.0]], [[40, 50.0]])
    assert "TICKER" in svc.books_cents
    assert svc.books_cents["TICKER"]["yes"] == [[60.0, 100.0], [50.0, 200.0]]
    assert svc.books_cents["TICKER"]["no"] == [[40.0, 50.0]]


def test_snapshot_converts_to_float():
    svc = make_service()
    svc._apply_snapshot("T", [[60, 10]], [[40, 5]])
    for entry in svc.books_cents["T"]["yes"]:
        assert all(isinstance(v, float) for v in entry)


def test_snapshot_skips_empty():
    svc = make_service()
    svc._apply_snapshot("T", [], [])
    assert "T" not in svc.books_cents


def test_snapshot_overwrites_existing():
    svc = make_service()
    svc.books_cents["T"] = {"yes": [[99, 1.0]], "no": []}
    svc._apply_snapshot("T", [[60, 10]], [[40, 5]])
    assert svc.books_cents["T"]["yes"] == [[60.0, 10.0]]


# ---------------------------------------------------------------------------
# _apply_delta — add new level
# ---------------------------------------------------------------------------

def test_delta_adds_new_price_level():
    svc = make_service()
    svc._apply_delta("T", {"price": "0.60", "delta": 100, "side": "yes"})
    assert svc.books_cents["T"]["yes"] == [[60, 100.0]]


def test_delta_uses_price_dollars_field():
    svc = make_service()
    svc._apply_delta("T", {"price_dollars": "0.40", "delta": 50, "side": "no"})
    assert svc.books_cents["T"]["no"] == [[40, 50.0]]


def test_delta_negative_on_empty_book_does_not_add():
    svc = make_service()
    svc._apply_delta("T", {"price": "0.50", "delta": -10, "side": "yes"})
    assert svc.books_cents.get("T", {}).get("yes", []) == []


# ---------------------------------------------------------------------------
# _apply_delta — update existing level
# ---------------------------------------------------------------------------

def test_delta_increases_existing_level():
    svc = make_service()
    svc.books_cents["T"] = {"yes": [[60, 100.0]], "no": []}
    svc._apply_delta("T", {"price": "0.60", "delta": 50, "side": "yes"})
    assert svc.books_cents["T"]["yes"][0][1] == 150.0


def test_delta_decreases_existing_level():
    svc = make_service()
    svc.books_cents["T"] = {"yes": [[60, 100.0]], "no": []}
    svc._apply_delta("T", {"price": "0.60", "delta": -30, "side": "yes"})
    assert svc.books_cents["T"]["yes"][0][1] == 70.0


def test_delta_removes_level_when_qty_reaches_zero():
    svc = make_service()
    svc.books_cents["T"] = {"yes": [[60, 100.0]], "no": []}
    svc._apply_delta("T", {"price": "0.60", "delta": -100, "side": "yes"})
    assert svc.books_cents["T"]["yes"] == []


def test_delta_book_sorted_best_bid_first():
    svc = make_service()
    svc._apply_delta("T", {"price": "0.30", "delta": 10, "side": "yes"})
    svc._apply_delta("T", {"price": "0.70", "delta": 20, "side": "yes"})
    svc._apply_delta("T", {"price": "0.50", "delta": 15, "side": "yes"})
    prices = [e[0] for e in svc.books_cents["T"]["yes"]]
    assert prices == sorted(prices, reverse=True)


# ---------------------------------------------------------------------------
# _apply_delta — guard conditions
# ---------------------------------------------------------------------------

def test_delta_missing_price_is_ignored():
    svc = make_service()
    svc._apply_delta("T", {"delta": 10, "side": "yes"})
    assert "T" not in svc.books_cents


def test_delta_bad_price_is_ignored():
    svc = make_service()
    svc._apply_delta("T", {"price": "not_a_number", "delta": 10, "side": "yes"})
    assert "T" not in svc.books_cents


def test_delta_zero_qty_is_ignored():
    svc = make_service()
    svc._apply_delta("T", {"price": "0.60", "delta": 0, "side": "yes"})
    assert svc.books_cents.get("T", {}).get("yes", []) == []


def test_delta_invalid_side_is_ignored():
    svc = make_service()
    svc._apply_delta("T", {"price": "0.60", "delta": 10, "side": "unknown"})
    assert "T" not in svc.books_cents
