"""
Tests for PolymarketWSWorker and WSManager (pure in-memory logic).

No WebSocket, no DB — all IO is replaced by asyncio.Queue mocks.
"""
import asyncio
from unittest.mock import AsyncMock

import pytest

from orderbook_service.polymarket.ws import PolymarketWSWorker, WSManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_worker(asset_ids, market_map=None):
    queue = asyncio.Queue()
    return PolymarketWSWorker(
        asset_ids=asset_ids,
        updates_queue=queue,
        market_map=market_map or {},
    ), queue


def make_manager(token_map=None):
    repo = AsyncMock()
    repo.get_token_ids_and_market_id.return_value = token_map or {}
    mgr = WSManager.__new__(WSManager)
    mgr.market_repository = repo
    mgr.updates_queue = asyncio.Queue()
    mgr.market_map = {}
    mgr.market_orderbooks = {}
    mgr.workers = []
    mgr._stop_event = asyncio.Event()
    return mgr


# ---------------------------------------------------------------------------
# PolymarketWSWorker._handle_message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_ignores_unknown_asset_id():
    worker, queue = make_worker(["known"], {"known": ("mkt-1", "yes")})
    await worker._handle_message({"asset_id": "unknown", "bids": [["0.5", "10"]]})
    assert queue.empty()


@pytest.mark.asyncio
async def test_handle_stores_bids_and_asks():
    worker, queue = make_worker(["a1"], {"a1": ("mkt-1", "yes")})
    await worker._handle_message({
        "asset_id": "a1",
        "bids": [["0.6", "100"]],
        "asks": [["0.7", "50"]],
    })
    assert worker.orderbooks["a1"]["bids"] == [["0.6", "100"]]
    assert worker.orderbooks["a1"]["asks"] == [["0.7", "50"]]


@pytest.mark.asyncio
async def test_handle_does_not_overwrite_bids_when_empty():
    worker, queue = make_worker(["a1"], {"a1": ("mkt-1", "yes")})
    worker.orderbooks["a1"]["bids"] = [["0.5", "10"]]
    await worker._handle_message({"asset_id": "a1", "bids": [], "asks": []})
    assert worker.orderbooks["a1"]["bids"] == [["0.5", "10"]]


@pytest.mark.asyncio
async def test_handle_puts_update_on_queue():
    worker, queue = make_worker(["a1"], {"a1": ("mkt-1", "yes")})
    await worker._handle_message({
        "asset_id": "a1",
        "bids": [["0.6", "100"]],
        "asks": [],
    })
    assert not queue.empty()
    market_id, side, ob = await queue.get()
    assert market_id == "mkt-1"
    assert side == "yes"
    assert ob["bids"] == [["0.6", "100"]]


@pytest.mark.asyncio
async def test_handle_no_market_map_entry_does_not_put():
    worker, queue = make_worker(["a1"], {})
    await worker._handle_message({"asset_id": "a1", "bids": [["0.5", "10"]]})
    assert queue.empty()


@pytest.mark.asyncio
async def test_handle_list_message_recurses():
    worker, queue = make_worker(["a1", "a2"], {
        "a1": ("mkt-1", "yes"),
        "a2": ("mkt-2", "no"),
    })
    await worker._handle_message([
        {"asset_id": "a1", "bids": [["0.5", "1"]]},
        {"asset_id": "a2", "asks": [["0.6", "2"]]},
    ])
    assert queue.qsize() == 2


# ---------------------------------------------------------------------------
# WSManager.load_mapping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_mapping_initialises_market_orderbooks():
    mgr = make_manager({
        "yes_token": ("mkt-1", "yes"),
        "no_token": ("mkt-1", "no"),
        "other_yes": ("mkt-2", "yes"),
    })
    await mgr.load_mapping()
    assert set(mgr.market_orderbooks.keys()) == {"mkt-1", "mkt-2"}
    assert mgr.market_orderbooks["mkt-1"] == {"yes": None, "no": None}


@pytest.mark.asyncio
async def test_load_mapping_stores_market_map():
    token_map = {"y1": ("mkt-1", "yes"), "n1": ("mkt-1", "no")}
    mgr = make_manager(token_map)
    await mgr.load_mapping()
    assert mgr.market_map == token_map


# ---------------------------------------------------------------------------
# WSManager.stop_inactive_workers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stop_inactive_workers_stops_disjoint_worker():
    mgr = make_manager()
    mgr.market_map = {"a1": ("mkt-1", "yes")}

    worker = AsyncMock()
    worker.asset_ids = ["a1"]
    mgr.workers = [worker]

    # new map no longer contains mkt-1
    new_map = {"a2": ("mkt-2", "yes")}
    await mgr.stop_inactive_workers(new_map)

    worker.stop.assert_awaited_once()
    assert mgr.workers == []


@pytest.mark.asyncio
async def test_stop_inactive_workers_keeps_overlapping_worker():
    mgr = make_manager()
    mgr.market_map = {"a1": ("mkt-1", "yes"), "a2": ("mkt-2", "no")}

    worker = AsyncMock()
    worker.asset_ids = ["a1"]
    mgr.workers = [worker]

    # mkt-1 is still in new map
    new_map = {"a1": ("mkt-1", "yes"), "a3": ("mkt-3", "yes")}
    await mgr.stop_inactive_workers(new_map)

    worker.stop.assert_not_awaited()
    assert mgr.workers == [worker]


@pytest.mark.asyncio
async def test_stop_inactive_workers_mixed():
    mgr = make_manager()
    mgr.market_map = {"a1": ("mkt-1", "yes"), "a2": ("mkt-2", "yes")}

    stale = AsyncMock()
    stale.asset_ids = ["a1"]  # mkt-1 gone

    active = AsyncMock()
    active.asset_ids = ["a2"]  # mkt-2 stays

    mgr.workers = [stale, active]
    new_map = {"a2": ("mkt-2", "yes")}
    await mgr.stop_inactive_workers(new_map)

    stale.stop.assert_awaited_once()
    active.stop.assert_not_awaited()
    assert mgr.workers == [active]
