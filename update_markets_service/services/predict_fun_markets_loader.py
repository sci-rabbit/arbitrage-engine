import asyncio
from typing import Any

import aiohttp
import structlog
from aiohttp_socks import ProxyConnector
from sqlalchemy.ext.asyncio import AsyncSession

from core import Market
from core.config import settings
from core.load_markets.db import batch_commit
from core.load_markets.fetcher import GetFetcher
from core.load_markets.loaders.load_predict_fun import load_predict_fun_markets
from core.load_markets.tasks import process_tasks
from core.market_parsers.predict_fun_parser import PredictFunParser
from core.models.database import get_ro_session
from core.repositories.market_repository import MarketRepository
from core.repositories.pair_repository import PairRepository

logger = structlog.getLogger(__name__)


POLL_INTERVAL = settings.predict_fun.poll_interval


class PredictFunLoaderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.max_concurrent_requests = settings.predict_fun.max_concurrency
        self.connector = (
            ProxyConnector.from_url(settings.predict_fun.proxy_url)
            if settings.predict_fun.proxy_url
            else None
        )
        self.fetcher = GetFetcher()
        self.url = settings.predict_fun.url

        self.markets_repo = MarketRepository(session=session)
        self.pairs_repo = PairRepository(session=session)

        self.existing_markets_map = {}

    def _process_market(self, raw_market: dict[str, Any]) -> dict[str, Any] | None:
        market_id = str(raw_market.get("id"))
        status = raw_market.get("status", "").upper()

        if market_id in self.existing_markets_map:
            existing_market = self.existing_markets_map.get(market_id)
            if existing_market:
                if status == "RESOLVED":
                    return {
                        "action": "delete",
                        "market_id": existing_market.platform_market_id,
                    }
                else:
                    return None

        if status not in ["REGISTERED", "OPEN"]:
            return None

        parsed = PredictFunParser.parse_market(raw=raw_market)

        return {"action": "save", "market": Market(**parsed)}

    async def load(self):
        total_fetched = 0
        total_saved = 0
        total_skipped = 0

        logger.info(
            "predict_fun.loader.start",
            url=self.url,
        )

        async with aiohttp.ClientSession(connector=self.connector) as aio_session:
            async for markets_raw in load_predict_fun_markets(
                aio_session=aio_session,
                fetcher=self.fetcher,
                url=self.url,
                max_concurrent_requests=self.max_concurrent_requests,
            ):
                raw_ids = [str(m.get("id")) for m in markets_raw]


                self.existing_markets_map = await self.markets_repo.get_map_by_ids(
                    platform="predict_fun",
                    market_ids=raw_ids,
                )

                results = process_tasks(
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
                    "predict_fun.loader.batch_processed",
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
                        "predict_fun.loader.transaction_failed",
                        error=str(e),
                        exc_info=True,
                    )
                    raise

        logger.info(
            "predict_fun.loader.finished",
            total_fetched=total_fetched,
            total_saved=total_saved,
            total_skipped=total_skipped,
        )


class PredictFunPollingService:

    @classmethod
    async def run(cls):
        logger.info("predict_fun_polling.start")

        while True:
            try:
                async with get_ro_session() as session:
                    service = PredictFunLoaderService(session=session)
                    await service.load()
            except Exception as e:
                logger.error("predict_fun_polling.error", error=str(e))

            await asyncio.sleep(POLL_INTERVAL)
