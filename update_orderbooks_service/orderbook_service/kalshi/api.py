import asyncio
from typing import List, Dict, Any, Optional

import aiohttp
import structlog
from aiohttp_socks import ProxyConnector

from core.config import settings
from core.fetcher import GetFetcher
from core.repositories.kalshi_repository import (
    KalshiRepository,
)
from core.models.database import get_ro_session

from core.orderbook_formatters.kalshi_formatter import format_kalshi_orderbook


from tasks.orderbooks import update_orderbooks_task

log = structlog.get_logger(__name__)


def _make_connector() -> Optional[ProxyConnector]:
    proxy_url = getattr(settings.kalshi, "proxy_url", None)
    if proxy_url:
        return ProxyConnector.from_url(proxy_url)
    return None

class KalshiOrderbookService:
    def __init__(self):
        self.base_url = settings.kalshi.url.replace("/markets", "")
        self.path = f"/markets/{{ticker}}/orderbook"
        self.orderbook_url_template = self.base_url + self.path
        self.poll_interval = getattr(settings.ws_worker, "UPDATE_INTERVAL", 5)
        self.markets_refresh_interval = getattr(
            settings.ws_worker, "MARKETS_REFRESH_INTERVAL", 30
        )
        self.batch_size = getattr(settings.ws_worker, "BATCH_SIZE", 20)
        self.max_concurrent_requests = settings.kalshi.max_concurrency
        self.headers = settings.kalshi.get_headers(path=self.path)
        self.active_tickers: List[str] = []
        self.orderbooks_cache: Dict[str, Dict[str, Any]] = {}
        self._stop_event = asyncio.Event()
        self.fetcher = GetFetcher()

    async def fetch_orderbook(
        self, session: aiohttp.ClientSession, ticker: str
    ) -> Optional[Dict[str, Any]]:
        url = self.orderbook_url_template.format(ticker=ticker)

        try:
            data = await self.fetcher.fetch_json(session, url, headers=self.headers)
            if not data:
                log.warning(
                    "Failed to fetch orderbook",
                    ticker=ticker,
                )
                return None

            formatted_orderbook = format_kalshi_orderbook(data)

            if not formatted_orderbook:
                log.debug(
                    "Empty orderbook skipped",
                    ticker=ticker,
                )
                return None

            log.info(
                "Fetched orderbook",
                ticker=ticker,
                formatted_orderbook=formatted_orderbook,
            )
            return formatted_orderbook

        except Exception as e:
            log.error(
                "Error fetching orderbook",
                ticker=ticker,
                error=str(e),
                exc_info=True,
            )
            return None

    async def fetch_orderbooks_batch(
        self, session: aiohttp.ClientSession, tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получить orderbooks для батча маркетов с ограничением concurrency.

        Args:
            session: aiohttp сессия
            tickers: Список tickers для запроса

        Returns:
            Словарь {ticker: orderbook}
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def fetch_with_semaphore(ticker: str):
            async with semaphore:
                orderbook = await self.fetch_orderbook(session, ticker)
                return ticker, orderbook

        tasks = [fetch_with_semaphore(ticker) for ticker in tickers]
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

            ticker, orderbook = result
            if orderbook:
                orderbooks[ticker] = orderbook

        return orderbooks

    async def refresh_active_markets(self) -> List[str]:
        """
        Обновить список активных маркетов из БД.

        Returns:
            Список активных tickers
        """
        try:
            async with get_ro_session() as session:
                repository = KalshiRepository(session=session)
                tickers = await repository.get_active_tickers_in_pairs()

            log.info(
                "Active markets refreshed",
                count=len(tickers),
                platform="kalshi",
            )
            return tickers
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
                            tickers=batch[:5],
                        )

                        orderbooks = await self.fetch_orderbooks_batch(session, batch)

                        for ticker, orderbook in orderbooks.items():
                            cached = self.orderbooks_cache.setdefault(
                                ticker,
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
            update_batch: Словарь {ticker: orderbook}
        """
        if not update_batch:
            return

        update_orderbooks_task.delay("kalshi", update_batch)
        log.info(
            "Celery task dispatched",
            count=len(update_batch),
            platform="kalshi",
        )

    async def run(self):
        log.info("Starting Kalshi Orderbook Service")

        self.active_tickers = await self.refresh_active_markets()

        if not self.active_tickers:
            log.warning("No active markets found, services will wait for markets")

        await asyncio.gather(
            self.poll_orderbooks(),
            self.refresh_markets_loop(),
        )

    async def stop(self):
        log.info("Stopping Kalshi Orderbook Service")
        self._stop_event.set()
