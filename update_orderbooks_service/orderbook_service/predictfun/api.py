import asyncio
from typing import List, Dict, Any, Optional

import aiohttp
import structlog
from aiohttp_socks import ProxyConnector

from core.config import settings
from core.fetcher import GetFetcher
from core.models.database import get_ro_session
from core.orderbook_formatters.predictfun_formatter import format_predictfun_orderbook

from tasks.orderbooks import update_orderbooks_task

from core.repositories.predictfun_repository import PredictfunRepository

log = structlog.get_logger(__name__)


def _make_connector() -> Optional[ProxyConnector]:
    proxy_url = getattr(settings.predict_fun, "proxy_url", None)
    if proxy_url:
        return ProxyConnector.from_url(proxy_url)
    return None

class PredictfunOrderbookService:
    def __init__(self):
        self.base_url = settings.predict_fun.url
        self.path = "/{market_id}/orderbook"
        self.orderbook_url_template = self.base_url + self.path
        self.poll_interval = getattr(settings.ws_worker, "UPDATE_INTERVAL", 5)
        self.markets_refresh_interval = getattr(
            settings.ws_worker, "MARKETS_REFRESH_INTERVAL", 30
        )
        self.batch_size = getattr(settings.ws_worker, "BATCH_SIZE", 20)
        self.max_concurrent_requests = 3
        self.headers = settings.predict_fun.get_headers()
        self.active_tickers: List[str] = []
        self.orderbooks_cache: Dict[str, Dict[str, Any]] = {}
        self._stop_event = asyncio.Event()
        self.fetcher = GetFetcher()

    async def fetch_orderbook(
        self, session: aiohttp.ClientSession, market_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получить orderbook для одного маркета через Predict.fun API.

        Args:
            session: aiohttp сессия
            market_id: ID маркета (platform_market_id)

        Returns:
            Отформатированный orderbook или None при ошибке
        """
        url = self.orderbook_url_template.format(market_id=market_id)

        try:
            data = await self.fetcher.fetch_json(session, url, headers=self.headers)
            if not data:
                log.warning(
                    "Failed to fetch orderbook",
                    market_id=market_id,
                )
                return None
            # Форматируем ответ API в единый формат
            formatted_orderbook = format_predictfun_orderbook(data)

            if not formatted_orderbook:
                log.debug(
                    "Empty orderbook skipped",
                    market_id=market_id,
                )
                return None

            log.info(
                "Fetched orderbook",
                market_id=market_id,
                formatted_orderbook=formatted_orderbook,
            )
            return formatted_orderbook

        except Exception as e:
            log.error(
                "Error fetching orderbook",
                market_id=market_id,
                error=str(e),
                exc_info=True,
            )
            return None

    async def fetch_orderbooks_batch(
        self, session: aiohttp.ClientSession, market_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получить orderbooks для батча маркетов с ограничением concurrency.

        Args:
            session: aiohttp сессия
            market_ids: Список market_ids для запроса

        Returns:
            Словарь {market_id: orderbook}
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def fetch_with_semaphore(market_id: str):
            async with semaphore:
                orderbook = await self.fetch_orderbook(session, market_id)
                return market_id, orderbook

        tasks = [fetch_with_semaphore(market_id) for market_id in market_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        orderbooks = {}
        for result in results:
            if isinstance(result, Exception):
                log.error(
                    "Exception in batch fetch",
                    error=str(result),
                    exc_info=result,
                )
                continue

            market_id, orderbook = result
            if orderbook:
                orderbooks[market_id] = orderbook

        return orderbooks

    async def refresh_active_markets(self) -> List[str]:
        """
        Обновить список активных маркетов из БД.

        Returns:
            Список активных market_ids
        """
        try:
            async with get_ro_session() as session:
                repository = PredictfunRepository(session=session)
                tickers = await repository.get_active_tickers_in_pairs()

            log.info(
                "Active markets refreshed",
                count=len(tickers),
                platform="predict_fun",
            )
            return tickers
        except ImportError:
            log.warning(
                "PredictfunRepository not found, skipping refresh",
                platform="predict_fun",
            )
            return self.active_tickers
        except Exception as e:
            log.error(
                "Error refreshing active markets",
                error=str(e),
                exc_info=True,
            )
            return self.active_tickers  # Возвращаем старый список при ошибке

    async def poll_orderbooks(self):
        """
        Основной цикл polling orderbooks.
        """
        async with aiohttp.ClientSession(connector=_make_connector()) as session:
            while not self._stop_event.is_set():
                try:
                    if not self.active_tickers:
                        log.warning("No active tickers, skipping poll cycle")
                        await asyncio.sleep(self.poll_interval)
                        continue

                    # Разбиваем на батчи для обработки
                    batches = [
                        self.active_tickers[i : i + self.batch_size]
                        for i in range(0, len(self.active_tickers), self.batch_size)
                    ]

                    for batch in batches:
                        if self._stop_event.is_set():
                            break

                        log.debug(
                            "Fetching orderbooks batch",
                            batch_size=len(batch),
                            market_ids=batch[:5],  # Логируем первые 5 для примера
                        )

                        orderbooks = await self.fetch_orderbooks_batch(session, batch)

                        # Обновляем кэш
                        for market_id, orderbook in orderbooks.items():
                            cached = self.orderbooks_cache.setdefault(
                                market_id,
                                {
                                    "yes": {"bids": [], "asks": []},
                                    "no": {"bids": [], "asks": []},
                                },
                            )

                            for side in ("yes", "no"):
                                if orderbook[side]["asks"]:
                                    cached[side]["asks"] = orderbook[side]["asks"]

                                if orderbook[side]["bids"]:
                                    cached[side]["bids"] = orderbook[side]["bids"]

                        # Небольшая задержка между батчами для rate limiting
                        await asyncio.sleep(0.5)

                    # Отправляем накопленные обновления в Celery
                    if self.orderbooks_cache:
                        self.dispatch_to_celery(self.orderbooks_cache.copy())
                        self.orderbooks_cache.clear()

                    await asyncio.sleep(self.poll_interval)

                except Exception as e:
                    log.error(
                        "Error in poll cycle",
                        error=str(e),
                        exc_info=True,
                    )
                    await asyncio.sleep(self.poll_interval)

    async def refresh_markets_loop(self):
        """
        Периодическое обновление списка активных маркетов.
        """
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.markets_refresh_interval)
                self.active_tickers = await self.refresh_active_markets()
            except Exception as e:
                log.error(
                    "Error in refresh markets loop",
                    error=str(e),
                    exc_info=True,
                )

    @staticmethod
    def dispatch_to_celery(update_batch: Dict[str, Dict[str, Any]]):
        """
        Отправить батч обновлений orderbook в Celery.

        Args:
            update_batch: Словарь {market_id: orderbook}
        """
        if not update_batch:
            return

        update_orderbooks_task.delay("predict_fun", update_batch)
        log.info(
            "Celery task dispatched",
            count=len(update_batch),
            platform="predict_fun",
        )

    async def run(self):
        """
        Запустить сервис обновления orderbooks.
        """
        log.info("Starting Predict.fun Orderbook Service")

        # Загружаем начальный список активных маркетов
        self.active_tickers = await self.refresh_active_markets()

        if not self.active_tickers:
            log.warning("No active markets found, services will wait for markets")

        # Запускаем параллельные задачи
        await asyncio.gather(
            self.poll_orderbooks(),
            self.refresh_markets_loop(),
        )

    async def stop(self):
        """
        Остановить сервис.
        """
        log.info("Stopping Predict.fun Orderbook Service")
        self._stop_event.set()


async def main():
    """
    Точка входа для запуска сервиса.
    """
    service = PredictfunOrderbookService()
    try:
        await service.run()
    except KeyboardInterrupt:
        log.info("Received interrupt signal")
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())

















