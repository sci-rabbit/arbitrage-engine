"""
Tests for PredictfunWSWorker._handle_message and _next_id.

No WebSocket, no DB — _handle_message is a pure async function that
reads from data and optionally puts onto updates_queue.
"""
import asyncio

import pytest

from orderbook_service.predictfun.ws_worker import PredictfunWSWorker

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_worker(market_ids=None):
    updates_queue = asyncio.Queue()
    new_markets_queue = asyncio.Queue()
    worker = PredictfunWSWorker(
        market_ids=market_ids or ["123"],
        updates_queue=updates_queue,
        new_markets_queue=new_markets_queue,
    )
    return worker, updates_queue


# ---------------------------------------------------------------------------
# _next_id
# ---------------------------------------------------------------------------

def test_next_id_increments():
    worker, _ = make_worker()
    assert worker._next_id() == 1
    assert worker._next_id() == 2
    assert worker._next_id() == 3


# ---------------------------------------------------------------------------
# _handle_message — guard conditions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ignores_non_M_type():
    worker, queue = make_worker()
    await worker._handle_message({"type": "R", "topic": "predictOrderbook/123"})
    assert queue.empty()


@pytest.mark.asyncio
async def test_ignores_non_orderbook_topic():
    worker, queue = make_worker()
    await worker._handle_message({"type": "M", "topic": "heartbeat"})
    assert queue.empty()


@pytest.mark.asyncio
async def test_ignores_missing_data():
    worker, queue = make_worker()
    await worker._handle_message({"type": "M", "topic": "predictOrderbook/123"})
    assert queue.empty()


@pytest.mark.asyncio
async def test_ignores_when_formatter_returns_none():
    worker, queue = make_worker()
    # formatter returns None when success=False or data is empty
    await worker._handle_message({
        "type": "M",
        "topic": "predictOrderbook/123",
        "data": {},  # format_predictfun_orderbook({success:True, data:{}}) → None
    })
    assert queue.empty()


# ---------------------------------------------------------------------------
# _handle_message — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_puts_formatted_orderbook_on_queue():
    worker, queue = make_worker(["999"])
    await worker._handle_message({
        "type": "M",
        "topic": "predictOrderbook/999",
        "data": {
            "marketId": 999,
            "bids": [[0.6, 100]],
            "asks": [[0.7, 50]],
        },
    })
    assert not queue.empty()
    market_id, formatted = await queue.get()
    assert market_id == "999"
    assert "yes" in formatted
    assert "no" in formatted


@pytest.mark.asyncio
async def test_extracts_market_id_from_topic():
    worker, queue = make_worker()
    await worker._handle_message({
        "type": "M",
        "topic": "predictOrderbook/42",
        "data": {
            "marketId": 42,
            "bids": [[0.5, 10]],
            "asks": [],
        },
    })
    market_id, _ = await queue.get()
    assert market_id == "42"


@pytest.mark.asyncio
async def test_formatted_result_has_correct_sides():
    worker, queue = make_worker()
    await worker._handle_message({
        "type": "M",
        "topic": "predictOrderbook/1",
        "data": {
            "bids": [[0.4, 200]],
            "asks": [[0.6, 100]],
        },
    })
    _, formatted = await queue.get()
    assert "bids" in formatted["yes"]
    assert "asks" in formatted["yes"]
    assert "bids" in formatted["no"]
    assert "asks" in formatted["no"]
