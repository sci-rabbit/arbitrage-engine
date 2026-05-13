from typing import Any, AsyncGenerator
import aiohttp
import structlog


from core.config import settings
from core.load_markets.fetcher import GetFetcher

logger = structlog.getLogger(__name__)


async def load_polymarket_markets(
    aio_session: aiohttp.ClientSession,
    fetcher: GetFetcher,
    limit: int = settings.polymarket.limit,
    url: str = settings.polymarket.url,
    volume_filter: int = settings.polymarket.volume_filter,
) -> AsyncGenerator[list[dict[str, Any]], Any]:
    logger.info(
        "polymarket.loader.start",
        limit=limit,
        volume_filter=volume_filter,
        url=url,
    )

    offset = 0

    while True:
        logger.info(
            "polymarket.loader.fetch_batch",
            offset=offset,
            limit=limit,
        )

        try:
            params = {
                "limit": limit,
                "offset": offset,
            }

            markets_raw = await fetcher.fetch_json(
                session=aio_session,
                url=url,
                params=params,
            )

            batch_count = len(markets_raw) if markets_raw else 0

            logger.info(
                "polymarket.loader.batch_received",
                offset=offset,
                received=batch_count,
            )

            if not markets_raw:
                break

            yield markets_raw

            logger.info(
                "polymarket.loader.batch_processed",
                offset=offset,
                received=batch_count,
            )

        finally:
            offset += limit


# @add_loader
# async def load_polymarket_markets(
#     aio_session: aiohttp.ClientSession,
#     fetcher: Callable[..., Awaitable[List[Dict[str, Any]]]],
#     limit: int = settings.polymarket.limit,
#     url: str = settings.polymarket.url,
#     volume_filter: int = settings.polymarket.volume_filter,
# ) -> None:
#     logger.info(
#         "polymarket.loader.start",
#         limit=limit,
#         volume_filter=volume_filter,
#         url=url,
#     )
#
#     offset = 0
#
#
#     while True:
#         logger.info(
#             "polymarket.loader.fetch_batch",
#             offset=offset,
#             limit=limit,
#         )
#
#         try:
#             params = {
#                 "limit": limit,
#                 "offset": offset,
#                 "closed": "false",
#             }
#
#             markets_raw = await fetcher(
#                 session=aio_session,
#                 url=url,
#                 params=params,
#             )
#
#             batch_count = len(markets_raw) if markets_raw else 0
#
#             logger.info(
#                 "polymarket.loader.batch_received",
#                 offset=offset,
#                 received=batch_count,
#             )
#
#             if not markets_raw:
#                 break
#
#             async def process_market(raw_market: Dict[str, Any]) -> Market | None:
#
#                 market_id = str(raw_market.get("id"))
#
#                 if market_id in existing_markets_ids:
#                     exists = await check_market_exists_and_update(
#                         market_id, raw_market, PolyMarketParser
#                     )
#                     if exists:
#                         return None
#
#                 prices = raw_market.get("outcomePrices")
#                 if prices and len(prices) == 2:
#                     yes = float(prices[0])
#                     no = float(prices[1])
#
#                     if yes <= 0.01 or no <= 0.01:
#                         return None
#
#                 close_time = raw_market.get("endDate")
#                 if close_time:
#                     close_time = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
#                     now = datetime.now(timezone.utc)
#
#                     if close_time <= now:
#                         return None
#
#                 volume = raw_market.get("volume") or raw_market.get("volume_num") or 0
#                 if get_float(volume) < volume_filter:
#                     return None
#
#                 parsed = PolyMarketParser.parse_market(raw=raw_market)
#
#                 return Market(**parsed)
#
#             results = await process_tasks(
#                 markets_raw=markets_raw,
#                 process_market=process_market,
#             )
#
#             saved = len(results)
#             skipped = batch_count - saved
#
#             total_saved += saved
#             total_skipped += skipped
#
#             logger.info(
#                 "polymarket.loader.batch_processed",
#                 offset=offset,
#                 received=batch_count,
#                 saved=saved,
#                 skipped=skipped,
#                 total_saved=total_saved,
#             )
#
#             await batch_commit(results, existing_markets_ids=existing_markets_ids)
#         finally:
#             offset += limit
#
#     logger.info(
#         "polymarket.loader.finished",
#         total_fetched=total_fetched,
#         total_saved=total_saved,
#         total_skipped=total_skipped,
#     )
