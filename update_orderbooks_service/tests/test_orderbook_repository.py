"""
Unit tests for OrderbookSyncRepository and OrderbookAsyncRepository.

Both classes contain the same merge logic; tests verify:
  - create path (no existing record)
  - None → wipes orderbook
  - dict + dict → merges, None values in incoming batch are skipped
  - non-dict (either side) → replaces outright
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.models.orderbooks import Orderbook
from core.repositories.orderbook_repository import (
    OrderbookAsyncRepository,
    OrderbookSyncRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ob(platform_market_id: str, orderbook=None) -> Orderbook:
    return Orderbook(platform_market_id=platform_market_id, orderbook=orderbook)


def _sync_repo():
    session = MagicMock()
    return OrderbookSyncRepository(session=session), session


def _async_repo():
    session = AsyncMock()
    session.add = MagicMock()  # AsyncSession.add() is synchronous
    return OrderbookAsyncRepository(session=session), session


def _mock_execute(session, existing: Orderbook | None):
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    session.execute.return_value = result


# ---------------------------------------------------------------------------
# OrderbookSyncRepository — create_orderbook
# ---------------------------------------------------------------------------

def test_sync_create_adds_to_session_and_flushes():
    repo, session = _sync_repo()
    obj = repo.create_orderbook("mkt-1", {"a": 1})
    session.add.assert_called_once_with(obj)
    session.flush.assert_called_once()
    assert obj.platform_market_id == "mkt-1"
    assert obj.orderbook == {"a": 1}


# ---------------------------------------------------------------------------
# OrderbookSyncRepository — update_orderbook
# ---------------------------------------------------------------------------

def test_sync_update_creates_when_not_found():
    repo, session = _sync_repo()
    session.query.return_value.filter.return_value.first.return_value = None
    obj = repo.update_orderbook("new-mkt", {"x": 1})
    session.add.assert_called_once()
    assert obj.platform_market_id == "new-mkt"


def test_sync_update_sets_none_clears_orderbook():
    repo, session = _sync_repo()
    existing = _ob("mkt-1", {"a": 1})
    session.query.return_value.filter.return_value.first.return_value = existing
    obj = repo.update_orderbook("mkt-1", None)
    assert obj.orderbook is None
    session.flush.assert_called_once()


def test_sync_update_merges_dicts():
    repo, session = _sync_repo()
    existing = _ob("mkt-1", {"a": 1, "b": 2})
    session.query.return_value.filter.return_value.first.return_value = existing
    obj = repo.update_orderbook("mkt-1", {"b": 99, "c": 3})
    assert obj.orderbook == {"a": 1, "b": 99, "c": 3}


def test_sync_update_skips_none_values_in_incoming_dict():
    repo, session = _sync_repo()
    existing = _ob("mkt-1", {"a": 1, "b": 2})
    session.query.return_value.filter.return_value.first.return_value = existing
    obj = repo.update_orderbook("mkt-1", {"a": None, "c": 5})
    assert obj.orderbook["a"] == 1   # not overwritten
    assert obj.orderbook["c"] == 5   # new key added


def test_sync_update_replaces_when_incoming_not_dict():
    repo, session = _sync_repo()
    existing = _ob("mkt-1", {"a": 1})
    session.query.return_value.filter.return_value.first.return_value = existing
    obj = repo.update_orderbook("mkt-1", "raw_string")
    assert obj.orderbook == "raw_string"


def test_sync_update_replaces_when_existing_not_dict():
    repo, session = _sync_repo()
    existing = _ob("mkt-1", "old_value")
    session.query.return_value.filter.return_value.first.return_value = existing
    obj = repo.update_orderbook("mkt-1", {"new": "data"})
    assert obj.orderbook == {"new": "data"}


# ---------------------------------------------------------------------------
# OrderbookAsyncRepository — upsert_orderbook
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_upsert_creates_when_not_found():
    repo, session = _async_repo()
    _mock_execute(session, None)
    obj = await repo.upsert_orderbook("new-mkt", {"x": 1})
    session.add.assert_called_once_with(obj)
    assert obj.platform_market_id == "new-mkt"


@pytest.mark.asyncio
async def test_async_upsert_sets_none():
    repo, session = _async_repo()
    existing = _ob("mkt-1", {"a": 1})
    _mock_execute(session, existing)
    obj = await repo.upsert_orderbook("mkt-1", None)
    assert obj.orderbook is None


@pytest.mark.asyncio
async def test_async_upsert_merges_dicts():
    repo, session = _async_repo()
    existing = _ob("mkt-1", {"a": 1, "b": 2})
    _mock_execute(session, existing)
    obj = await repo.upsert_orderbook("mkt-1", {"b": 99, "c": 3})
    assert obj.orderbook == {"a": 1, "b": 99, "c": 3}


@pytest.mark.asyncio
async def test_async_upsert_skips_none_values_in_incoming():
    repo, session = _async_repo()
    existing = _ob("mkt-1", {"a": 1})
    _mock_execute(session, existing)
    obj = await repo.upsert_orderbook("mkt-1", {"a": None, "b": 5})
    assert obj.orderbook["a"] == 1
    assert obj.orderbook["b"] == 5


@pytest.mark.asyncio
async def test_async_upsert_replaces_when_not_dict():
    repo, session = _async_repo()
    existing = _ob("mkt-1", {"a": 1})
    _mock_execute(session, existing)
    obj = await repo.upsert_orderbook("mkt-1", "flat_value")
    assert obj.orderbook == "flat_value"
