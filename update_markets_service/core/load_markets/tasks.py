import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from core.models import Market

logger = structlog.getLogger(__name__)


def results_handler(result: list[Any]) -> list[Any]:
    clear_results = []
    for r in result:
        if r is None:
            continue
        if isinstance(r, Exception):
            logger.exception(
                "Something went wrong while filling database",
                error=str(r),
                exc_info=r,
            )
            continue

        clear_results.append(r)

    return clear_results


async def async_process_tasks(
    markets_raw: list[dict[str, Any]],
    process_market: Callable[..., Awaitable[Market | None]],
) -> list[dict[str, Any]]:
    tasks = [
        asyncio.create_task(process_market(market_raw)) for market_raw in markets_raw
    ]
    results: list[Market | None] = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    return results_handler(results)


def process_tasks(
    markets_raw: list[dict[str, Any]],
    process_market: Callable[[Any], Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = [
        process_market(market_raw) for market_raw in markets_raw
    ]

    return results_handler(results)
