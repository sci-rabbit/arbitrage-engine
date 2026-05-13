import asyncio
from concurrent.futures import ProcessPoolExecutor

import orjson
import structlog
from typing import List

from core.config import settings
from core.redis.redis_cli import RedisService
from core.repositories.orderbook_repository import OrderbookRepository
from core.repositories.pair_repository import PairRepository
from core.schemas.arbitrage import ArbitrageResult, ArbitrageOpportunity
from core.schemas.markets import MarketShort
from core.utils import generate_market_url
from services.arbitrage import check_arbitrage
from core.models.database import get_rw_session

logger = structlog.getLogger(__name__)


_GENERIC_LABELS = {"yes", "no", "true", "false"}


def _get_labels(market) -> list:
    outcomes = market.outcomes
    if isinstance(outcomes, list):
        return outcomes  # polymarket stores outcomes as plain list
    if isinstance(outcomes, dict):
        return outcomes.get("labels", [])
    return []


def _is_sports(market) -> bool:
    outcomes = market.outcomes
    # predict.fun: outcomes dict has raw list with team objects
    if isinstance(outcomes, dict):
        if any(o.get("team") for o in outcomes.get("raw", [])):
            return True
    # any platform: first label is a team name, not generic yes/no
    labels = _get_labels(market)
    return bool(labels) and labels[0].lower() not in _GENERIC_LABELS


def _outcomes_reversed(market_a, market_b) -> bool:
    if not (_is_sports(market_a) and _is_sports(market_b)):
        return False
    a_labels = _get_labels(market_a)
    b_labels = _get_labels(market_b)
    if len(a_labels) == 2 and len(b_labels) == 2:
        return a_labels[0].lower() != b_labels[0].lower()
    return False


def _flip_orderbook(ob: dict) -> dict:
    return {"yes": ob["no"], "no": ob["yes"]}


class ArbitrageTask:
    def __init__(self, redis_service: RedisService):
        cfg = settings.arbitrage

        self.redis_service = redis_service
        self.executor = ProcessPoolExecutor(max_workers=cfg.max_workers)

        self.price_threshold: float = cfg.price_threshold
        self.min_size: float = cfg.min_size
        self.threshold_distance: float = cfg.threshold_distance
        self.threshold_final_score: float = cfg.threshold_final_score
        self.cache_ttl: int = cfg.cache_ttl

    async def compute_and_store(self):
        """Вычисляем арбитраж и сохраняем в Redis"""
        logger.info(
            "arbitrage_scan_started",
            price_threshold=self.price_threshold,
            min_size=self.min_size,
        )

        async with get_rw_session() as db_session:
            pair_repo = PairRepository(session=db_session)
            orderbook_repo = OrderbookRepository(session=db_session)

            pairs_with_markets = await pair_repo.get_all_pairs_with_markets(
                threshold_distance=self.threshold_distance,
                threshold_final_score=self.threshold_final_score,
            )

            if not pairs_with_markets:
                await self.redis_service.set("arb:global", orjson.dumps([]), ex=self.cache_ttl)
                return

            market_ids = {
                m.platform_market_id
                for _, markets in pairs_with_markets
                for m in markets
            }
            orderbooks_list = await orderbook_repo.get_by_platform_market_ids(
                list(market_ids)
            )
            orderbooks_map = {ob.platform_market_id: ob for ob in orderbooks_list}

        results: List[ArbitrageResult] = []

        loop = asyncio.get_running_loop()

        tasks = []
        task_metadata = []

        for pair_obj, markets in pairs_with_markets:
            try:
                if len(markets) < 2:
                    continue

                market_a, market_b = markets
                ob1 = orderbooks_map.get(market_a.platform_market_id)
                ob2 = orderbooks_map.get(market_b.platform_market_id)

                if not ob1 or not ob2:
                    continue

                ob1_data = ob1.orderbook
                ob2_data = ob2.orderbook
                if _outcomes_reversed(market_a, market_b):
                    ob2_data = _flip_orderbook(ob2_data)

                payload = loop.run_in_executor(
                    self.executor,
                    check_arbitrage,
                    ob1_data,
                    ob2_data,
                    self.min_size,
                    self.price_threshold,
                )
                tasks.append(payload)
                task_metadata.append((pair_obj, market_a, market_b))

            except Exception as e:
                logger.error("arbitrage_pair_failed", pair_id=pair_obj.id, error=str(e))
                continue

        if not tasks:
            return

        all_opportunities = await asyncio.gather(*tasks, return_exceptions=True)

        for (pair_obj, market_a, market_b), opportunities in zip(
            task_metadata, all_opportunities
        ):
            if isinstance(opportunities, Exception):
                logger.error(
                    "arbitrage_pair_failed",
                    pair_id=pair_obj.id,
                    error=str(opportunities),
                )
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

        if results:
            data_to_cache = [r.model_dump() for r in results]
            await self.redis_service.set(
                "arb:global", orjson.dumps(data_to_cache), ex=self.cache_ttl
            )
        else:
            await self.redis_service.set("arb:global", orjson.dumps([]), ex=self.cache_ttl)

        logger.info("arbitrage_scan_completed", count=len(results))

    async def run_forever(self, interval: float = 5):
        while True:
            try:
                await self.compute_and_store()
            except Exception as e:
                logger.error("arbitrage_task_failed", error=str(e), exc_info=True)
            await asyncio.sleep(interval)
