import asyncio
from datetime import UTC, datetime
from typing import Any

import aiohttp
import structlog
from aiohttp_socks import ProxyConnector
from sqlalchemy.ext.asyncio import AsyncSession

from core import Market
from core.config import settings
from core.load_markets.converters import get_float
from core.load_markets.db import batch_commit
from core.load_markets.fetcher import GetFetcher
from core.load_markets.loaders.load_polymarket import load_polymarket_markets
from core.load_markets.tasks import process_tasks
from core.market_parsers.polymarket_parser import PolyMarketParser
from core.models.database import get_ro_session
from core.repositories.market_repository import MarketRepository
from core.repositories.pair_repository import PairRepository

logger = structlog.getLogger(__name__)

POLL_INTERVAL = settings.polymarket.poll_interval


class PolymarketLoaderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.max_concurrent_requests = settings.polymarket.max_concurrency
        self.connector = (
            ProxyConnector.from_url(settings.polymarket.proxy_url)
            if settings.polymarket.proxy_url
            else None
        )
        self.fetcher = GetFetcher()
        self.url = settings.polymarket.url

        self.markets_repo = MarketRepository(session=session)
        self.pairs_repo = PairRepository(session=session)

        self.existing_markets_map = {}

    def _process_market(self, raw_market: dict[str, Any]) -> dict[str, Any] | None:
        market_id = str(raw_market.get("id"))
        closed = raw_market.get("closed", False)

        if market_id in self.existing_markets_map:
            existing_market = self.existing_markets_map.get(market_id)
            if existing_market:
                if closed:
                    return {
                        "action": "delete",
                        "market_id": existing_market.platform_market_id,
                    }
                else:
                    return None
        if closed:
            return None

        prices = raw_market.get("outcomePrices")
        if prices and len(prices) == 2:
            yes = float(prices[0])
            no = float(prices[1])

            if yes <= 0.01 or no <= 0.01:
                return None

        close_time = raw_market.get("endDate")
        if close_time:
            close_time = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
            now = datetime.now(UTC)

            if close_time <= now:
                return None

        volume = raw_market.get("volume") or raw_market.get("volume_num") or 0
        if get_float(volume) < settings.polymarket.volume_filter:
            return None


        parsed = PolyMarketParser.parse_market(raw=raw_market)

        return {"action": "save", "market": Market(**parsed)}

    async def load(self):
        total_fetched = 0
        total_saved = 0
        total_skipped = 0

        logger.info(
            "polymarket.loader.start",
            url=self.url,
        )

        async with aiohttp.ClientSession(connector=self.connector) as aio_session:
            async for markets_raw in load_polymarket_markets(
                aio_session=aio_session,
                fetcher=self.fetcher,
                url=self.url,
            ):
                raw_ids = [str(m.get("id")) for m in markets_raw]

                self.existing_markets_map = await self.markets_repo.get_map_by_ids(
                    platform="polymarket",
                    market_ids=raw_ids,
                )

                results = process_tasks(
                    markets_raw=markets_raw,
                    process_market=self._process_market,
                )
                to_commit = [
                    result["market"] for result in results if result["action"] == "save"
                ]
                _to_delete = [
                    result["market_id"]
                    for result in results
                    if result["action"] == "delete"
                ]

                batch_count = len(markets_raw) if markets_raw else 0
                total_fetched += batch_count

                saved = len(to_commit)
                skipped = len(markets_raw) - saved

                total_saved += saved
                total_skipped += skipped

                logger.info(
                    "polymarket.loader.batch_processed",
                    received=batch_count,
                    saved=saved,
                    skipped=skipped,
                    total_saved=total_saved,
                )

                try:
                    if to_commit:
                        await batch_commit(
                            db_session=self.session,
                            results=to_commit,
                        )
                    await self.session.commit()
                except Exception as e:
                    await self.session.rollback()
                    logger.error(
                        "polymarket.loader.transaction_failed",
                        error=str(e),
                        exc_info=True,
                    )
                    raise

        logger.info(
            "polymarket.loader.finished",
            total_fetched=total_fetched,
            total_saved=total_saved,
            total_skipped=total_skipped,
        )


class PolymarketPollingService:

    @classmethod
    async def run(cls):
        logger.info("polymarket_polling.start")

        while True:
            try:
                async with get_ro_session() as session:
                    service = PolymarketLoaderService(session=session)
                    await service.load()
            except Exception as e:
                logger.error("polymarket_polling.error", error=str(e))

            await asyncio.sleep(POLL_INTERVAL)
