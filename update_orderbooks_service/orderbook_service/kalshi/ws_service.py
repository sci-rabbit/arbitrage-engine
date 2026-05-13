import asyncio
from typing import Any

import structlog

from core.config import settings
from core.models.database import get_ro_session, get_rw_session
from core.orderbook_formatters.kalshi_formatter import format_kalshi_orderbook
from core.repositories.kalshi_repository import KalshiRepository
from core.repositories.orderbook_repository import OrderbookAsyncRepository
from orderbook_service.kalshi.ws_worker import KalshiWSWorker

log = structlog.get_logger(__name__)


class KalshiWSService:

    def __init__(self):
        self.poll_interval = getattr(settings.ws_worker, "UPDATE_INTERVAL", 5)
        self.markets_refresh_interval = getattr(
            settings.ws_worker, "MARKETS_REFRESH_INTERVAL", 30
        )
        self.active_tickers: list[str] = []
        self.books_cents: dict[str, dict[str, list[list[float]]]] = {}
        self._stop_event = asyncio.Event()

    async def refresh_active_markets(self) -> list[str]:
        try:
            async with get_ro_session() as session:
                repo = KalshiRepository(session=session)
                tickers = await repo.get_active_tickers_in_pairs()

            log.info(
                "KalshiWSService.active_markets_refreshed",
                count=len(tickers),
            )
            return tickers
        except Exception as e:
            log.error(
                "KalshiWSService.refresh_active_markets.error",
                error=str(e),
                exc_info=True,
            )
            return self.active_tickers

    def _apply_snapshot(self, ticker: str, yes: list[list[float]], no: list[list[float]]):
        yes_levels = len(yes)
        no_levels = len(no)
        log.debug(
            "KalshiWSService.apply_snapshot",
            ticker=ticker,
            yes_levels=yes_levels,
            no_levels=no_levels,
        )
        if yes_levels == 0 and no_levels == 0:
            log.debug("KalshiWSService.skip_empty_snapshot", ticker=ticker)
            return
        self.books_cents[ticker] = {
            "yes": [[float(p), float(q)] for p, q in yes],
            "no": [[float(p), float(q)] for p, q in no],
        }

    def _apply_delta(self, ticker: str, delta_msg: dict[str, Any]):
        """
        Применяем дельту: price (в центах), delta (изменение контракта), side ('yes'/'no').
        Kalshi WS v2 шлёт price_dollars / delta_fp.
        """
        raw_price = delta_msg.get("price") or delta_msg.get("price_dollars")
        if raw_price is None:
            log.debug(
                "KalshiWSService.delta_missing_price", ticker=ticker, msg=delta_msg
            )
            return
        try:
            # price_dollars -> центы, чтобы быть совместимым со снапшотом
            price = int(round(float(raw_price) * 100))
        except (TypeError, ValueError):
            log.debug("KalshiWSService.delta_bad_price", ticker=ticker, price=raw_price)
            return

        raw_delta = delta_msg.get("delta")
        if raw_delta is None:
            raw_delta = delta_msg.get("delta_fp")
        try:
            qty_delta = float(raw_delta or 0)
        except (TypeError, ValueError):
            log.debug("KalshiWSService.delta_bad_delta", ticker=ticker, delta=raw_delta)
            return

        side = delta_msg.get("side")
        if side not in ("yes", "no") or qty_delta == 0:
            return

        book = self.books_cents.setdefault(ticker, {"yes": [], "no": []})
        side_book = book[side]

        # ищем уровень по цене
        for entry in side_book:
            if entry[0] == price:
                new_qty = entry[1] + qty_delta
                if new_qty <= 0:
                    side_book.remove(entry)
                else:
                    entry[1] = new_qty
                break
        else:
            # не нашли такой уровень — если дельта > 0, добавляем
            if qty_delta > 0:
                side_book.append([price, qty_delta])

        # сортируем: bids от высокой цены к низкой
        side_book.sort(key=lambda x: -x[0])

    async def _consumer_loop(self, updates_queue: asyncio.Queue) -> None:
        """
        Получает snapshots/deltas из очереди и периодически шлёт
        нормализованные ордербуки в Celery.
        """
        while not self._stop_event.is_set():
            try:
                # ждём хотя бы одно сообщение или таймаут
                try:
                    ticker, kind, payload = await asyncio.wait_for(
                        updates_queue.get(), timeout=self.poll_interval
                    )
                    log.debug("KalshiWSService.message", ticker=ticker, kind=kind, keys=list((payload or {}).keys()))
                    if kind == "snapshot":
                        yes = payload.get("yes") or []
                        no  = payload.get("no") or []
                        self._apply_snapshot(ticker, yes, no)
                    elif kind == "delta":
                        self._apply_delta(ticker, payload)
                except TimeoutError:
                    pass

                while not updates_queue.empty():
                    ticker, kind, payload = await updates_queue.get()
                    if kind == "snapshot":
                        yes = payload.get("yes") or []
                        no  = payload.get("no") or []
                        self._apply_snapshot(ticker, yes, no)
                    elif kind == "delta":
                        self._apply_delta(ticker, payload)

                if not self.books_cents:
                    log.debug("KalshiWSService.no_books_yet")
                    continue

                # нормализуем и шлём только те тикеры, по которым есть данные
                batch: dict[str, dict[str, Any]] = {}
                for ticker, book in self.books_cents.items():
                    yes = book.get("yes") or []
                    no = book.get("no") or []
                    if not yes and not no:
                        continue
                    api_like = {"orderbook": {"yes": yes, "no": no}}
                    formatted = format_kalshi_orderbook(api_like)
                    if formatted:
                        batch[ticker] = formatted

                if batch:
                    tickers = list(batch.keys())
                    log.info(
                        "KalshiWSService.batch_ready",
                        count=len(batch),
                        tickers=tickers,
                    )
                    async with get_rw_session() as session:
                        repo = OrderbookAsyncRepository(session)
                        for ticker, ob in batch.items():
                            await repo.upsert_orderbook(ticker, ob)
                    log.info(
                        "KalshiWSService.db_committed",
                        count=len(batch),
                        tickers=tickers,
                    )
            except Exception as e:
                log.error(
                    "KalshiWSService.consumer_loop.error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(self.poll_interval)

    async def _refresh_markets_loop(self, new_tickers_queue: asyncio.Queue) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.markets_refresh_interval)
                refreshed = await self.refresh_active_markets()
                added = [t for t in refreshed if t not in set(self.active_tickers)]
                if added:
                    log.info("KalshiWSService.new_tickers_found", count=len(added))
                    await new_tickers_queue.put(added)
                self.active_tickers = refreshed
            except Exception as e:
                log.error(
                    "KalshiWSService.refresh_markets_loop.error",
                    error=str(e),
                    exc_info=True,
                )

    async def run(self) -> None:
        log.info("KalshiWSService.start")

        self.active_tickers = await self.refresh_active_markets()
        if not self.active_tickers:
            log.warning("KalshiWSService.no_active_markets")

        updates_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.ws_worker.UPDATES_QUEUE_MAX_SIZE)
        new_tickers_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.ws_worker.NEW_MARKETS_QUEUE_MAX_SIZE)
        worker = KalshiWSWorker(self.active_tickers, updates_queue, new_tickers_queue)

        await asyncio.gather(
            worker.connect(),
            self._consumer_loop(updates_queue),
            self._refresh_markets_loop(new_tickers_queue),
        )

    async def stop(self) -> None:
        self._stop_event.set()
        log.info("KalshiWSService.stop")
