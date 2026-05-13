import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

import aiohttp
import structlog
from aiohttp_socks import ProxyConnector
from sqlalchemy.ext.asyncio import AsyncSession

from core import Market
from core.config import settings
from core.load_markets.converters import get_float
from core.load_markets.db import batch_commit
from core.load_markets.fetcher import GetFetcher
from core.load_markets.loaders.load_kalshi import (
    fetch_series_ticker,
    load_kalshi_markets,
)
from core.load_markets.tasks import async_process_tasks
from core.market_parsers.kalshi_parser import KalshiParser
from core.models.database import get_ro_session
from core.repositories.market_repository import MarketRepository
from core.repositories.pair_repository import PairRepository

logger = structlog.getLogger(__name__)


POLL_INTERVAL = settings.kalshi.poll_interval


class KalshiLoaderService:
    def __init__(self, session: AsyncSession):
        self.aio_session = None
        self.session = session
        self.max_concurrent_requests = settings.kalshi.max_concurrency
        self.connector = (
            ProxyConnector.from_url(settings.kalshi.proxy_url)
            if settings.kalshi.proxy_url
            else None
        )
        self.fetcher = GetFetcher()
        self.url = settings.kalshi.url
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        self.markets_repo = MarketRepository(session=session)
        self.pairs_repo = PairRepository(session=session)

        self.existing_markets_map = {}

    async def _process_market(
        self, raw_market: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        market_id = str(raw_market.get("ticker"))
        status = raw_market.get("status", "")

        if market_id in self.existing_markets_map:
            existing_market = self.existing_markets_map.get(market_id)
            if existing_market:
                if status not in ("open", "active"):
                    return {
                        "action": "delete",
                        "market_id": existing_market.platform_market_id,
                    }
                else:
                    return None

        if status not in ("open", "active"):
            return None
            
        close_time = raw_market.get("close_time")
        if close_time:
            close_time = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            if close_time <= now:
                return None

        volume = raw_market.get("volume_fp") or 0
        if get_float(volume) < settings.kalshi.volume_filter:
            return None

        event_ticker = raw_market.get("event_ticker")
        if event_ticker:
            async with self.semaphore:
                _, series_ticker = await fetch_series_ticker(
                    event_ticker,
                    self.aio_session,
                    self.fetcher,
                )

            if series_ticker:
                raw_market["series_ticker"] = series_ticker

        parsed = KalshiParser.parse_market(raw=raw_market)

        return {"action": "save", "market": Market(**parsed)}

    async def load(self):
        total_fetched = 0
        total_saved = 0
        total_skipped = 0

        logger.info(
            "kalshi.loader.start",
            limit=settings.kalshi.limit,
            volume_filter=settings.kalshi.volume_filter,
            url=self.url,
        )

        async with aiohttp.ClientSession(connector=self.connector) as aio_session:
            self.aio_session = aio_session

            async for markets_raw in load_kalshi_markets(
                aio_session=aio_session,
                fetcher=self.fetcher,
                url=self.url,
            ):
                raw_ids = [str(m.get("ticker")) for m in markets_raw]

                self.existing_markets_map = await self.markets_repo.get_map_by_ids(
                    platform="kalshi",
                    market_ids=raw_ids,
                )

                results = await async_process_tasks(
                    markets_raw=markets_raw,
                    process_market=self._process_market,
                )
                to_commit = [
                    result["market"] for result in results if result["action"] == "save"
                ]
                to_delete = [
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
                    "kalshi.loader.batch_processed",
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
                    if to_delete:
                        await self.pairs_repo.delete_many(platform_market_ids=to_delete)
                        await self.markets_repo.delete_many(
                            platform_market_ids=to_delete
                        )
                    await self.session.commit()
                except Exception as e:
                    await self.session.rollback()
                    logger.error(
                        "kalshi.loader.transaction_failed",
                        error=str(e),
                        exc_info=True,
                    )
                    raise

        logger.info(
            "kalshi.loader.finished",
            total_fetched=total_fetched,
            total_saved=total_saved,
            total_skipped=total_skipped,
        )


class KalshiPollingService:

    @classmethod
    async def run(cls):
        logger.info("kalshi_polling.start")

        while True:
            try:
                async with get_ro_session() as session:
                    service = KalshiLoaderService(session=session)
                    await service.load()
            except Exception as e:
                logger.error("kalshi_polling.error", error=str(e), exc_info=True)

            await asyncio.sleep(POLL_INTERVAL)
