import asyncio
from typing import Any

import structlog

from core.config import settings
from core.models.database import get_ro_session, get_rw_session
from core.repositories.orderbook_repository import OrderbookAsyncRepository
from core.repositories.predictfun_repository import PredictfunRepository
from orderbook_service.predictfun.ws_worker import PredictfunWSWorker

log = structlog.get_logger(__name__)


class PredictfunWSService:
    """
    Продакшн‑сервис ордербуков Predict.fun на WebSocket.

    - Достаёт список активных market_ids из БД.
    - Открывает одно WS‑соединение и подписывается на них.
    - Полученные ордербуки нормализованы в формате format_predictfun_orderbook и
      периодически отправляются в Celery (update_orderbooks_task).
    """

    def __init__(self):
        self.poll_interval = getattr(settings.ws_worker, "UPDATE_INTERVAL", 5)
        self.markets_refresh_interval = getattr(
            settings.ws_worker, "MARKETS_REFRESH_INTERVAL", 30
        )
        self.active_market_ids: list[str] = []
        self.orderbooks_cache: dict[str, dict[str, Any]] = {}
        self._stop_event = asyncio.Event()

    async def refresh_active_markets(self) -> list[str]:
        try:
            async with get_ro_session() as session:
                repo = PredictfunRepository(session=session)
                market_ids = await repo.get_active_tickers_in_pairs()

            log.info(
                "PredictfunWSService.active_markets_refreshed",
                count=len(market_ids),
            )
            return market_ids
        except Exception as e:
            log.error(
                "PredictfunWSService.refresh_active_markets.error",
                error=str(e),
                exc_info=True,
            )
            return self.active_market_ids

    async def _consumer_loop(self, updates_queue: asyncio.Queue) -> None:
        """
        Получает нормализованные ордербуки из очереди и периодически шлёт их в Celery.
        """
        while not self._stop_event.is_set():
            try:
                # собираем апдейты в течение poll_interval
                try:
                    market_id, orderbook = await asyncio.wait_for(
                        updates_queue.get(), timeout=self.poll_interval
                    )
                    self.orderbooks_cache[market_id] = orderbook
                except TimeoutError:
                    pass

                # сгребаем всё, что накопилось в очереди
                while not updates_queue.empty():
                    market_id, orderbook = await updates_queue.get()
                    self.orderbooks_cache[market_id] = orderbook

                if self.orderbooks_cache:
                    batch = self.orderbooks_cache.copy()
                    self.orderbooks_cache.clear()

                    async with get_rw_session() as session:
                        repo = OrderbookAsyncRepository(session)
                        for mid, ob in batch.items():
                            await repo.upsert_orderbook(mid, ob)
                    log.info("PredictfunWSService.db_committed", count=len(batch))
            except Exception as e:
                log.error(
                    "PredictfunWSService.consumer_loop.error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(self.poll_interval)

    async def _refresh_markets_loop(self, new_markets_queue: asyncio.Queue) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.markets_refresh_interval)
                refreshed = await self.refresh_active_markets()
                added = [m for m in refreshed if m not in set(self.active_market_ids)]
                if added:
                    log.info("PredictfunWSService.new_markets_found", count=len(added))
                    await new_markets_queue.put(added)
                self.active_market_ids = refreshed
            except Exception as e:
                log.error(
                    "PredictfunWSService.refresh_markets_loop.error",
                    error=str(e),
                    exc_info=True,
                )

    async def run(self) -> None:
        log.info("PredictfunWSService.start")

        self.active_market_ids = await self.refresh_active_markets()
        if not self.active_market_ids:
            log.warning("PredictfunWSService.no_active_markets")

        updates_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.ws_worker.UPDATES_QUEUE_MAX_SIZE)
        new_markets_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.ws_worker.NEW_MARKETS_QUEUE_MAX_SIZE)
        worker = PredictfunWSWorker(self.active_market_ids, updates_queue, new_markets_queue)

        await asyncio.gather(
            worker.connect(),
            self._consumer_loop(updates_queue),
            self._refresh_markets_loop(new_markets_queue),
        )

    async def stop(self) -> None:
        self._stop_event.set()
        log.info("PredictfunWSService.stop")

