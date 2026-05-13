"""Tests for MarketService dispatch and platform-specific services."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.market_service.service import MarketService
from services.market_service.service_storage import services_storage

# ---------------------------------------------------------------------------
# MarketService dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_market_service_dispatches_to_registered_service():
    mock_cls = MagicMock()
    mock_instance = AsyncMock()
    mock_instance.search = AsyncMock(return_value=["m1"])
    mock_cls.return_value = mock_instance
    session = AsyncMock()

    with patch.dict(services_storage, {"test_plat": mock_cls}):
        svc = MarketService(common_id="abc", platform="test_plat", session=session)
        result = await svc.search()

    mock_cls.assert_called_once_with(session=session)
    mock_instance.search.assert_called_once_with(common_id="abc")
    assert result == ["m1"]


@pytest.mark.asyncio
async def test_market_service_passes_session_to_platform_service():
    mock_cls = MagicMock()
    mock_instance = AsyncMock()
    mock_instance.search = AsyncMock(return_value=[])
    mock_cls.return_value = mock_instance
    session = AsyncMock()

    with patch.dict(services_storage, {"plat": mock_cls}):
        svc = MarketService(common_id="x", platform="plat", session=session)
        await svc.search()

    _, kwargs = mock_cls.call_args
    assert kwargs["session"] is session


@pytest.mark.asyncio
async def test_market_service_unknown_platform_raises_key_error():
    session = AsyncMock()
    svc = MarketService(common_id="x", platform="nonexistent_xyz", session=session)
    with pytest.raises(KeyError):
        await svc.search()


# ---------------------------------------------------------------------------
# KalshiService — uppercases common_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kalshi_service_uppercases_common_id():
    repo = AsyncMock()
    repo.search = AsyncMock(return_value=[])
    session = AsyncMock()
    with patch("services.market_service.kalshi_service.KalshiRepository", return_value=repo):
        from services.market_service.kalshi_service import KalshiService
        svc = KalshiService(session=session)
        await svc.search(common_id="mkt-abc-123")
    repo.search.assert_called_once_with(common_id="MKT-ABC-123")


@pytest.mark.asyncio
async def test_kalshi_service_already_uppercase_unchanged():
    repo = AsyncMock()
    repo.search = AsyncMock(return_value=[])
    session = AsyncMock()
    with patch("services.market_service.kalshi_service.KalshiRepository", return_value=repo):
        from services.market_service.kalshi_service import KalshiService
        svc = KalshiService(session=session)
        await svc.search(common_id="MKT-1")
    repo.search.assert_called_once_with(common_id="MKT-1")


# ---------------------------------------------------------------------------
# PolymarketService — passes common_id as-is
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_polymarket_service_passes_common_id_unchanged():
    repo = AsyncMock()
    repo.search = AsyncMock(return_value=[])
    session = AsyncMock()
    with patch("services.market_service.polymarket_service.PolymarketRepository", return_value=repo):
        from services.market_service.polymarket_service import PolymarketService
        svc = PolymarketService(session=session)
        await svc.search(common_id="0xAbCdEf")
    repo.search.assert_called_once_with(common_id="0xAbCdEf")


# ---------------------------------------------------------------------------
# PredictfunService — passes common_id as-is
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predictfun_service_passes_common_id_unchanged():
    repo = AsyncMock()
    repo.search = AsyncMock(return_value=[])
    session = AsyncMock()
    with patch("services.market_service.predictfun_service.PredictfunRepository", return_value=repo):
        from services.market_service.predictfun_service import PredictfunService
        svc = PredictfunService(session=session)
        await svc.search(common_id="some-event-slug")
    repo.search.assert_called_once_with(common_id="some-event-slug")
