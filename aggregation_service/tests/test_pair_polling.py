"""Tests for PairPollingService.start_polling."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from polling_new_pairs import PairPollingService


def _make_service():
    pair_gen = AsyncMock()
    pair_gen.generate_and_store = AsyncMock(return_value=0)
    session = AsyncMock()
    svc = PairPollingService(pair_generation_service=pair_gen, session=session)
    return svc, pair_gen, session


@pytest.mark.asyncio
async def test_start_polling_calls_generate_and_store():
    svc, pair_gen, _ = _make_service()
    call_count = 0

    async def fake_generate(limit, offset):
        nonlocal call_count
        call_count += 1
        svc.running = False
        return 5

    pair_gen.generate_and_store.side_effect = fake_generate

    with patch("asyncio.sleep", new=AsyncMock()):
        await svc.start_polling(limit=100)

    assert call_count == 1


@pytest.mark.asyncio
async def test_start_polling_advances_offset_on_results():
    svc, pair_gen, _ = _make_service()
    offsets = []
    call_count = 0

    async def fake_generate(limit, offset):
        nonlocal call_count
        offsets.append(offset)
        call_count += 1
        if call_count >= 2:
            svc.running = False
        return 10  # non-zero → advance offset

    pair_gen.generate_and_store.side_effect = fake_generate

    with patch("asyncio.sleep", new=AsyncMock()):
        await svc.start_polling(limit=100)

    assert offsets[0] == 0
    assert offsets[1] == 100


@pytest.mark.asyncio
async def test_start_polling_resets_offset_when_no_results():
    svc, pair_gen, _ = _make_service()
    offsets = []
    call_count = 0

    async def fake_generate(limit, offset):
        nonlocal call_count
        offsets.append(offset)
        call_count += 1
        if call_count >= 2:
            svc.running = False
        return 0  # zero → reset offset to 0

    pair_gen.generate_and_store.side_effect = fake_generate

    with patch("asyncio.sleep", new=AsyncMock()):
        await svc.start_polling(limit=100)

    assert offsets[0] == 0
    assert offsets[1] == 0


@pytest.mark.asyncio
async def test_start_polling_calls_rollback_on_exception():
    svc, pair_gen, session = _make_service()
    call_count = 0

    async def fake_generate(limit, offset):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("DB error")
        svc.running = False
        return 0

    pair_gen.generate_and_store.side_effect = fake_generate

    with patch("asyncio.sleep", new=AsyncMock()):
        await svc.start_polling(limit=100)

    session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_start_polling_continues_after_exception():
    svc, pair_gen, _ = _make_service()
    call_count = 0

    async def fake_generate(limit, offset):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")
        svc.running = False
        return 0

    pair_gen.generate_and_store.side_effect = fake_generate

    with patch("asyncio.sleep", new=AsyncMock()):
        await svc.start_polling(limit=100)

    assert call_count == 2  # continued after exception


@pytest.mark.asyncio
async def test_stop_polling_sets_running_false():
    svc, _, _ = _make_service()
    svc.running = True
    await svc.stop_polling()
    assert svc.running is False