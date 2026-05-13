"""Tests for batch_commit batching logic."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.load_markets.db import batch_commit


def _markets(n: int):
    return [MagicMock() for _ in range(n)]


def _session_with_capture():
    session = AsyncMock()
    session.add_all = MagicMock()  # add_all is synchronous on AsyncSession
    call_sizes = []
    session.add_all.side_effect = lambda items: call_sizes.append(len(items))
    return session, call_sizes


@pytest.mark.asyncio
async def test_batch_commit_empty_does_nothing():
    session = AsyncMock()
    session.add_all = MagicMock()
    await batch_commit(session, [])
    session.add_all.assert_not_called()
    session.flush.assert_not_called()


@pytest.mark.asyncio
async def test_batch_commit_small_batch_single_flush():
    session, call_sizes = _session_with_capture()
    await batch_commit(session, _markets(10))
    assert call_sizes == [10]
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_batch_commit_exactly_50_single_flush():
    session, call_sizes = _session_with_capture()
    await batch_commit(session, _markets(50))
    assert call_sizes == [50]
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_batch_commit_51_items_two_flushes():
    session, call_sizes = _session_with_capture()
    await batch_commit(session, _markets(51))
    assert call_sizes == [50, 1]
    assert session.flush.call_count == 2


@pytest.mark.asyncio
async def test_batch_commit_75_items_correct_split():
    session, call_sizes = _session_with_capture()
    await batch_commit(session, _markets(75))
    assert call_sizes == [50, 25]
    assert session.flush.call_count == 2


@pytest.mark.asyncio
async def test_batch_commit_100_items_two_equal_flushes():
    session, call_sizes = _session_with_capture()
    await batch_commit(session, _markets(100))
    assert call_sizes == [50, 50]
    assert session.flush.call_count == 2
