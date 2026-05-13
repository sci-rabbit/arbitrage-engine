import asyncio
from collections.abc import Callable, Awaitable
from typing import List, Any, Dict

import structlog

from core.models import Market

logger = structlog.getLogger(__name__)


def results_handler(result: List[Any]) -> List[Any]:
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
    markets_raw: List[Dict[str, Any]],
    process_market: Callable[..., Awaitable[Market | None]],
) -> List[Dict[str, Any]]:
    tasks = [
        asyncio.create_task(process_market(market_raw)) for market_raw in markets_raw
    ]
    results: List[Market | None] = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    return results_handler(results)


def process_tasks(
    markets_raw: List[Dict[str, Any]],
    process_market: Callable[[Any], Any],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = [
        process_market(market_raw) for market_raw in markets_raw
    ]

    return results_handler(results)