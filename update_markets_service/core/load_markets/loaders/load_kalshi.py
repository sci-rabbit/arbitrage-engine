import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import structlog
from sqlalchemy import select, update

from core.config import settings
from core.load_markets.fetcher import GetFetcher
from core.models import Market
from core.models.database import get_ro_session

logger = structlog.getLogger(__name__)


async def fetch_series_ticker(
    event_ticker: str,
    aio_session: aiohttp.ClientSession,
    fetcher: GetFetcher,
    max_concurrent_requests: int = 5,
) -> tuple[str, str | None]:
    events_url = f"{settings.kalshi.events_url}/{event_ticker}"
    try:
        event_payload = await fetcher.fetch_json(
            session=aio_session,
            url=events_url,
            params={},
        )

        event_data = event_payload.get("event", {})
        series_ticker = event_data.get("series_ticker")
        logger.info(f"kalshi.loader.series_ticker: {series_ticker}")
        return event_ticker, series_ticker
    except Exception as e:
        logger.warning(
            "kalshi.loader.failed_to_fetch_series_ticker",
            event_ticker=event_ticker,
            error=str(e),
            exc_info=True,
        )
        return event_ticker, None


async def load_kalshi_markets(
    aio_session: aiohttp.ClientSession,
    fetcher: GetFetcher,
    limit: int = settings.kalshi.limit,
    url: str = settings.kalshi.url,
    max_concurrent_requests: int = 5,
) -> AsyncGenerator[Any, Any]:

    cursor = None

    params = {
        "limit": limit,
    }

    while True:
        try:
            if cursor:
                params["cursor"] = cursor

            logger.info(
                "kalshi.loader.fetch_batch",
                cursor=cursor,
                limit=limit,
            )
            async with asyncio.Semaphore(value=max_concurrent_requests):
                payload = await fetcher.fetch_json(
                    session=aio_session,
                    url=url,
                    params=params,
                )

            markets_raw = payload.get("markets", [])
            next_cursor = payload.get("cursor")

            batch_count = len(markets_raw)

            logger.info(
                "kalshi.loader.batch_received",
                cursor=cursor,
                received=batch_count,
                next_cursor=bool(next_cursor),
            )

            if not markets_raw:
                logger.info("kalshi.loader.no_more_markets")
                break

            yield markets_raw

            if not next_cursor:
                logger.info("kalshi.loader.cursor_finished")
                break

            cursor = next_cursor

        except Exception as e:
            logger.exception(
                "kalshi.loader.error",
                error=str(e),
                exc_info=True,
            )
            break


async def main():
    fetcher = GetFetcher()

    async with aiohttp.ClientSession() as aio_session:
        async with get_ro_session() as session:
            query = (
                select(Market)
                .where(Market.platform == "kalshi")
                .where(
                    Market.series_ticker.is_(None),
                )
            )

            res = await session.execute(query)
            markets = res.scalars().all()
            logger.info("Markets - ", count=len(markets))

        async def task(aioh_session, market):
            async with get_ro_session() as tsession:
                event_ticker = market.event_id
                if event_ticker:
                    _, series_ticker = await fetch_series_ticker(
                        event_ticker, aioh_session, fetcher
                    )
                    await tsession.execute(
                        update(Market)
                        .where(Market.id == market.id)
                        .values(series_ticker=series_ticker)
                    )
                    await tsession.commit()

        tasks = [asyncio.create_task(task(aio_session, market)) for market in markets]
        res = await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
