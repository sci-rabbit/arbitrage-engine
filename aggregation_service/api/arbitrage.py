import orjson
import structlog
import redis.exceptions

from typing import List

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.database import get_ro_session

from api.deps import require_access
from core.repositories.pair_repository import PairRepository
from core.repositories.orderbook_repository import OrderbookRepository
from core.repositories.market_repository import MarketRepository
from core.schemas.arbitrage import ArbitrageResult, ArbitrageOpportunity
from core.schemas.markets import MarketShort
from core.utils.url_generator import generate_market_url
from services.arbitrage import check_arbitrage

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])


@router.get("/scan", response_model=List[ArbitrageResult])
async def scan_arbitrage(
    price_threshold: float = Query(0.97),
    min_size: float = Query(25),
    threshold_distance: float = Query(0.7),
    threshold_final_score: float = Query(0.7),
    db_session: AsyncSession = Depends(get_ro_session),
) -> List[ArbitrageResult]:
    logger.info(
        "arbitrage_scan_started", price_threshold=price_threshold, min_size=min_size
    )

    pair_repo = PairRepository(session=db_session)
    orderbook_repo = OrderbookRepository(session=db_session)

    pairs_with_markets = await pair_repo.get_all_pairs_with_markets(
        threshold_distance=threshold_distance,
        threshold_final_score=threshold_final_score,
    )
    logger.info("pairs_fetched", total_pairs=len(pairs_with_markets))

    if not pairs_with_markets:
        return []

    market_ids = {
        m.platform_market_id for _, markets in pairs_with_markets for m in markets
    }
    orderbooks_list = await orderbook_repo.get_by_platform_market_ids(list(market_ids))
    orderbooks_map = {ob.platform_market_id: ob for ob in orderbooks_list}

    results: List[ArbitrageResult] = []

    for pair_obj, markets in pairs_with_markets:
        if len(markets) < 2:
            continue

        market_a, market_b = markets
        market_a_id = market_a.platform_market_id
        market_b_id = market_b.platform_market_id

        ob1 = orderbooks_map.get(market_a_id)
        ob2 = orderbooks_map.get(market_b_id)

        if not ob1 or not ob2:
            continue

        try:
            opportunities = check_arbitrage(
                ob1.orderbook,
                ob2.orderbook,
                min_size=min_size,
                price_threshold=price_threshold,
            )
        except Exception:
            continue

        if not opportunities:
            continue

        opp_models = [
            ArbitrageOpportunity(
                direction=opp["direction"],
                entry_price_1=opp["entry_price_1"],
                entry_price_2=opp["entry_price_2"],
                entry_spread=opp["entry_spread"],
                min_size_per_market=opp["min_size_per_market"],
                min_spread=opp["min_spread"],
                avg_sum_at_min_spread=opp["avg_sum_at_min_spread"],
                pnl_at_min_spread=opp["pnl_at_min_spread"],
                max_spread=opp["max_spread"],
                avg_sum_at_max_spread=opp["avg_sum_at_max_spread"],
                pnl_at_max_spread=opp["pnl_at_max_spread"],
                final_contracts=opp["final_contracts"],
                final_cost=opp["final_cost"],
                final_avg_price=opp["final_avg_price"],
                final_spread=opp["final_spread"],
                final_pnl=opp["final_pnl"],
            )
            for opp in opportunities
        ]

        results.append(
            ArbitrageResult(
                distance=float(pair_obj.distance or 0),
                final_score=float(pair_obj.final_score or 0),
                market_a=MarketShort(
                    platform=market_a.platform,
                    platform_market_id=market_a.platform_market_id,
                    title=market_a.title,
                    description=market_a.description,
                    close_time=market_a.close_time,
                    url=generate_market_url(
                        platform=market_a.platform,
                        platform_market_id=market_a.platform_market_id,
                        event_slug=market_a.event_slug,
                        event_id=market_a.event_id,
                        series_ticker=market_a.series_ticker,
                    ),
                ),
                market_b=MarketShort(
                    platform=market_b.platform,
                    platform_market_id=market_b.platform_market_id,
                    title=market_b.title,
                    description=market_b.description,
                    close_time=market_b.close_time,
                    url=generate_market_url(
                        platform=market_b.platform,
                        platform_market_id=market_b.platform_market_id,
                        event_slug=market_b.event_slug,
                        event_id=market_b.event_id,
                        series_ticker=market_b.series_ticker,
                    ),
                ),
                arbitrage=opp_models,
            )
        )

    logger.info("arbitrage_scan_completed", total_opportunities=len(results))
    return results


@router.get("/stats")
async def get_arbitrage_stats(request: Request):
    """Public endpoint for landing-page stats — no auth required."""
    redis_service = request.app.state.redis_service
    try:
        raw = await redis_service.get("arb:global")
    except redis.exceptions.ConnectionError:
        return {"count": 0, "best_spread": 0.0, "platforms": 0}
    if not raw:
        return {"count": 0, "best_spread": 0.0, "platforms": 0}

    data = orjson.loads(raw)
    spreads: list[float] = []
    platforms: set[str] = set()
    for item in data:
        for opp in item.get("arbitrage", []):
            spreads.append(opp.get("min_spread", 0.0))
        for key in ("market_a", "market_b"):
            platform = item.get(key, {}).get("platform")
            if platform:
                platforms.add(platform)

    return {
        "count": len(spreads),
        "best_spread": max(spreads) if spreads else 0.0,
        "platforms": len(platforms),
    }


@router.get("/scan_cache", dependencies=[Depends(require_access)])
async def scan_arbitrage_cache(request: Request) -> List[ArbitrageResult]:
    redis_service = request.app.state.redis_service
    try:
        raw = await redis_service.get("arb:global")
    except redis.exceptions.ConnectionError as e:
        logger.warning("redis_unavailable_fallback", error=str(e))
        return []
    if not raw:
        return []
    return orjson.loads(raw)


@router.get("/compute", response_model=List[ArbitrageOpportunity])
async def compute_arbitrage(
    platform_market_id_a: str,
    platform_market_id_b: str,
    price_threshold: float = Query(0.97),
    min_size: float = Query(25),
    db_session: AsyncSession = Depends(get_ro_session),
) -> List[ArbitrageOpportunity]:
    """
    Compute arbitrage opportunities between two specific markets by platform_market_id.
    Returns only arbitrage legs (no pair metadata).
    """
    orderbook_repo = OrderbookRepository(session=db_session)
    orderbooks = await orderbook_repo.get_by_platform_market_ids(
        [platform_market_id_a, platform_market_id_b]
    )
    orderbooks_map = {ob.platform_market_id: ob for ob in orderbooks}

    ob1 = orderbooks_map.get(platform_market_id_a)
    ob2 = orderbooks_map.get(platform_market_id_b)
    if not ob1 or not ob2 or not ob1.orderbook or not ob2.orderbook:
        return []

    opportunities = check_arbitrage(
        ob1.orderbook,
        ob2.orderbook,
        min_size=min_size,
        price_threshold=price_threshold,
    )

    return [
        ArbitrageOpportunity(
            direction=opp["direction"],
            entry_price_1=opp["entry_price_1"],
            entry_price_2=opp["entry_price_2"],
            entry_spread=opp["entry_spread"],
            min_size_per_market=opp["min_size_per_market"],
            min_spread=opp["min_spread"],
            avg_sum_at_min_spread=opp["avg_sum_at_min_spread"],
            pnl_at_min_spread=opp["pnl_at_min_spread"],
            max_spread=opp["max_spread"],
            avg_sum_at_max_spread=opp["avg_sum_at_max_spread"],
            pnl_at_max_spread=opp["pnl_at_max_spread"],
            final_contracts=opp["final_contracts"],
            final_cost=opp["final_cost"],
            final_avg_price=opp["final_avg_price"],
            final_spread=opp["final_spread"],
            final_pnl=opp["final_pnl"],
        )
        for opp in (opportunities or [])
    ]
