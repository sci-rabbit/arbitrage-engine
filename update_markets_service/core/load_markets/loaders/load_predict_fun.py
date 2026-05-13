import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import structlog

from core.config import settings
from core.load_markets.fetcher import GetFetcher

logger = structlog.getLogger(__name__)


async def load_predict_fun_markets(
    aio_session: aiohttp.ClientSession,
    fetcher: GetFetcher,
    url: str = settings.predict_fun.url,
    max_concurrent_requests: int = 5,
) -> AsyncGenerator[list[dict[str, Any]] | list[Any] | Any, Any]:

    cursor = None

    headers = settings.predict_fun.get_headers()

    while True:
        logger.info(
            "predict_fun.loader.fetch_batch",
            cursor=cursor,
        )

        try:
            params = {}

            if cursor:
                params["after"] = cursor

            async with asyncio.Semaphore(value=max_concurrent_requests):
                response = await fetcher.fetch_json(
                    session=aio_session,
                    url=url,
                    params=params,
                    headers=headers,
                )

            if isinstance(response, dict):
                if not response.get("success", False):
                    logger.warning("predict_fun.loader.api_error", response=response)
                    break

                markets_raw = response.get("data", [])
                next_cursor = response.get("cursor")
            else:
                markets_raw = response if isinstance(response, list) else []
                next_cursor = None

            batch_count = len(markets_raw) if markets_raw else 0

            logger.info(
                "predict_fun.loader.batch_received",
                cursor=cursor,
                received=batch_count,
            )

            if not markets_raw:
                break

            yield markets_raw

            cursor = next_cursor

        except Exception as e:
            logger.exception(
                "predict_fun.loader.error",
                error=str(e),
                exc_info=True,
            )
            break
