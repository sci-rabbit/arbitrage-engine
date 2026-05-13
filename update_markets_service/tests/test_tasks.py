"""Tests for results_handler, process_tasks, async_process_tasks."""
import pytest

from core.load_markets.tasks import async_process_tasks, process_tasks, results_handler

# ---------------------------------------------------------------------------
# results_handler
# ---------------------------------------------------------------------------

def test_results_handler_empty():
    assert results_handler([]) == []


def test_results_handler_filters_none():
    assert results_handler([None, None]) == []


def test_results_handler_filters_exceptions():
    assert results_handler([Exception("boom"), ValueError("x")]) == []


def test_results_handler_passes_valid_items():
    obj = {"action": "save"}
    result = results_handler([None, obj, Exception("x")])
    assert result == [obj]


def test_results_handler_preserves_order():
    items = [{"id": 1}, {"id": 2}, {"id": 3}]
    result = results_handler([items[0], None, items[1], Exception("e"), items[2]])
    assert result == items


# ---------------------------------------------------------------------------
# process_tasks
# ---------------------------------------------------------------------------

def test_process_tasks_calls_process_market_for_each():
    calls = []

    def proc(raw):
        calls.append(raw)
        return {"action": "save"}

    markets = [{"id": "1"}, {"id": "2"}]
    result = process_tasks(markets, proc)
    assert calls == markets
    assert len(result) == 2


def test_process_tasks_filters_none_returns():
    result = process_tasks([{"id": "1"}, {"id": "2"}], lambda x: None)
    assert result == []


def test_process_tasks_propagates_exception():
    def fail(_):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        process_tasks([{"id": "1"}], fail)


# ---------------------------------------------------------------------------
# async_process_tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_process_tasks_collects_results():
    async def proc(raw):
        return {"id": raw["id"]}

    markets = [{"id": "a"}, {"id": "b"}]
    result = await async_process_tasks(markets, proc)
    assert len(result) == 2
    ids = {r["id"] for r in result}
    assert ids == {"a", "b"}


@pytest.mark.asyncio
async def test_async_process_tasks_filters_none():
    async def proc(raw):
        return None

    result = await async_process_tasks([{"id": "1"}, {"id": "2"}], proc)
    assert result == []


@pytest.mark.asyncio
async def test_async_process_tasks_filters_exceptions():
    async def proc(raw):
        if raw.get("fail"):
            raise ValueError("oops")
        return {"id": raw["id"]}

    markets = [{"id": "1"}, {"id": "2", "fail": True}]
    result = await async_process_tasks(markets, proc)
    assert len(result) == 1
    assert result[0]["id"] == "1"


@pytest.mark.asyncio
async def test_async_process_tasks_empty_input():
    async def proc(raw):
        return raw

    result = await async_process_tasks([], proc)
    assert result == []
