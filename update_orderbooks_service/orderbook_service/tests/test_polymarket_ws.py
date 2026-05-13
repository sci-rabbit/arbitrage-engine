import asyncio

import structlog

from orderbook_service.polymarket.ws import PolymarketWSWorker

log = structlog.get_logger(__name__)


ASYNC_ASSET_IDS: list[str] = [
    "96292701313700591758244756869796264483122104108648861038158096856523650425510",
    "102055354858414185480457136339361588264019296944085790991211802364942028665034",
]

WATCHDOG_TIMEOUT_SECONDS = 60


async def run_once() -> None:
    """
    Single run of worker + consumer with watchdog:
    - if no messages for WATCHDOG_TIMEOUT_SECONDS, restart WS connection.
    """
    updates_queue: asyncio.Queue = asyncio.Queue()

    # In this test we don't map to internal market ids/sides, just pass dummy map
    market_map = {aid: (aid, "yes") for aid in ASYNC_ASSET_IDS}

    worker = PolymarketWSWorker(
        asset_ids=ASYNC_ASSET_IDS,
        updates_queue=updates_queue,
        market_map=market_map,
    )

    async def consumer() -> None:
        while True:
            try:
                market_id, side, orderbook = await asyncio.wait_for(
                    updates_queue.get(), timeout=WATCHDOG_TIMEOUT_SECONDS
                )
            except TimeoutError:
                log.warning(
                    "test_polymarket_ws.watchdog_timeout",
                    timeout_seconds=WATCHDOG_TIMEOUT_SECONDS,
                )
                # Прерываемся, чтобы снаружи перезапустить worker.connect()
                raise

            log.info(
                "test_polymarket_ws.orderbook",
                market_id=market_id,
                side=side,
                orderbook=orderbook,
            )

    worker_task = asyncio.create_task(worker.connect())
    consumer_task = asyncio.create_task(consumer())

    done, pending = await asyncio.wait(
        {worker_task, consumer_task}, return_when=asyncio.FIRST_EXCEPTION
    )

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Пробрасываем первое исключение (если было), чтобы вызвать рестарт в основном цикле
    for task in done:
        exc = task.exception()
        if exc:
            raise exc


async def main() -> None:
    while True:
        try:
            await run_once()
        except TimeoutError:
            # watchdog: перезапускаем цикл
            log.info("test_polymarket_ws.restart_after_timeout")
            continue


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("test_polymarket_ws: interrupted by user")

