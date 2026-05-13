"""
Tests for PolymarketRepository.get_token_ids_and_market_id.

The method calls get_active_markets_in_pairs() and builds a
token_id → (platform_market_id, side) mapping.
We patch get_active_markets_in_pairs to avoid DB.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from core.models.markets import Market
from core.repositories.poly_repository import PolymarketRepository


def _market(platform_market_id: str, token_ids) -> Market:
    m = Market(
        platform="polymarket",
        platform_market_id=platform_market_id,
        event_id="evt",
        token_ids=json.dumps(token_ids) if not isinstance(token_ids, str) else token_ids,
    )
    return m


async def _repo_with_markets(markets):
    session = AsyncMock()
    repo = PolymarketRepository(session=session)
    with patch.object(repo, "get_active_markets_in_pairs", AsyncMock(return_value=markets)):
        result = await repo.get_token_ids_and_market_id()
    return result


# ---------------------------------------------------------------------------
# Mapping logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_maps_yes_and_no_tokens():
    market = _market("mkt-1", ["yes_token", "no_token"])
    mapping = await _repo_with_markets([market])

    assert mapping["yes_token"] == ("mkt-1", "yes")
    assert mapping["no_token"] == ("mkt-1", "no")


@pytest.mark.asyncio
async def test_multiple_markets_all_mapped():
    markets = [
        _market("mkt-1", ["y1", "n1"]),
        _market("mkt-2", ["y2", "n2"]),
    ]
    mapping = await _repo_with_markets(markets)
    assert len(mapping) == 4
    assert mapping["y2"] == ("mkt-2", "yes")
    assert mapping["n1"] == ("mkt-1", "no")


@pytest.mark.asyncio
async def test_skips_token_ids_with_wrong_length():
    markets = [
        _market("mkt-bad", ["only_one"]),
        _market("mkt-ok", ["y", "n"]),
    ]
    mapping = await _repo_with_markets(markets)
    assert len(mapping) == 2
    assert "only_one" not in mapping


@pytest.mark.asyncio
async def test_skips_empty_token_ids():
    market = _market("mkt-empty", [])
    mapping = await _repo_with_markets([market])
    assert mapping == {}


@pytest.mark.asyncio
async def test_empty_markets_returns_empty_mapping():
    mapping = await _repo_with_markets([])
    assert mapping == {}


@pytest.mark.asyncio
async def test_later_market_overwrites_same_token():
    # If two markets share a token_id, last one wins (dict assignment)
    markets = [
        _market("mkt-1", ["shared", "n1"]),
        _market("mkt-2", ["shared", "n2"]),
    ]
    mapping = await _repo_with_markets(markets)
    assert mapping["shared"] == ("mkt-2", "yes")