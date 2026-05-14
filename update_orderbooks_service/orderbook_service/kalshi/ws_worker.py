"""
Kalshi WebSocket — подписка на orderbook по market_ticker.

Документация:
  https://docs.kalshi.com/api-reference/websockets/orderbook-updates
  https://docs.kalshi.com/api-reference/websockets/websocket-connection

Endpoint: wss://api.elections.kalshi.com/trade-api/ws/v2 (требуется auth в заголовках)

Канал: orderbook_delta
  Подписка: {"id": 1, "cmd": "subscribe", "params": {"channels": ["orderbook_delta"], "market_tickers": [...]}}

Типы сообщений:
  - orderbook_snapshot — первый снимок при подписке; msg.yes / msg.no — [[price_cents, size], ...]
  - orderbook_delta    — инкремент; msg: market_ticker, price (центы), delta, side ("yes"|"no")

Статусы: в канале orderbook событий «маркет закрыт» нет. Статусы маркетов (open/closed/settled) —
  через REST: https://docs.kalshi.com/api-reference/market/get-markets
"""
import asyncio
import time
from typing import Any

import aiohttp
import structlog
from aiohttp import WSMsgType
from aiohttp_socks import ProxyConnector

from core.config import settings
from core.kalshi_utils import dollars_fp_to_cents
from core.models.database import get_ro_session
from core.repositories.kalshi_repository import KalshiRepository

log = structlog.get_logger(__name__)

WATCHDOG_TIMEOUT_SECONDS = 60
PERIODIC_RECONNECT_SECONDS = 600


def _make_connector() -> ProxyConnector | None:
    proxy_url = getattr(settings.kalshi, "proxy_url", None)
    if proxy_url:
        return ProxyConnector.from_url(proxy_url)
    return None


class KalshiWSWorker:
    """
    WS‑клиент Kalshi для подписки на orderbook_delta по нескольким тикерам сразу.

    В продакшн‑режиме прокидывает snapshot/delta в очередь обновлений.
    """

    def __init__(
        self,
        tickers: list[str],
        updates_queue: asyncio.Queue,
        new_tickers_queue: asyncio.Queue,
    ):
        self.tickers: list[str] = list(tickers)
        self.updates_queue = updates_queue
        self.new_tickers_queue = new_tickers_queue
        self.url = settings.kalshi.ws_url
        self.headers = settings.kalshi.get_headers(
            method="GET",
            path="/trade-api/ws/v2",
        )
        self._sub_id = 0
        self._last_msg_ts: float | None = None

    def _next_id(self) -> int:
        self._sub_id += 1
        return self._sub_id

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse, tickers: list[str]) -> None:
        if not tickers:
            return
        msg = {
            "id": self._next_id(),
            "cmd": "subscribe",
            "params": {
                "channels": ["orderbook_delta"],
                "market_tickers": tickers,
            },
        }
        await ws.send_json(msg)
        log.info("KalshiWSWorker: subscribed", tickers=tickers)

    async def _dynamic_subscribe_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """Досылает subscribe для новых тикеров в уже открытое соединение."""
        while True:
            new_tickers = await self.new_tickers_queue.get()
            if not new_tickers:
                continue
            try:
                await self._subscribe(ws, new_tickers)
                self.tickers.extend(new_tickers)
            except Exception as e:
                log.error("KalshiWSWorker: dynamic subscribe failed", error=str(e))
                await self.new_tickers_queue.put(new_tickers)
                return

    async def _handle_message(self, data: dict[str, Any]) -> None:
        msg_type = data.get("type")
        msg = data.get("msg") or {}
        ticker = msg.get("market_ticker") or msg.get("ticker")

        if msg_type not in ("orderbook_snapshot", "orderbook_delta") or not ticker:
            return

        if msg_type == "orderbook_snapshot":
            yes_fp = msg.get("yes_dollars_fp") or msg.get("yes") or []
            no_fp  = msg.get("no_dollars_fp") or msg.get("no") or []
            yes = dollars_fp_to_cents(yes_fp)
            no  = dollars_fp_to_cents(no_fp)
            await self.updates_queue.put(
                (ticker, "snapshot", {"yes": yes, "no": no})
            )
        else:
            await self.updates_queue.put((ticker, "delta", msg))


    async def connect(self) -> None:
        """
        Открывает одно WS‑соединение и держит подписку на все тикеры.
        При обрыве — ре(connect) с экспоненциальной паузой.
        """
        delay = 1.0

        while True:
            try:
                log.info(
                    "KalshiWSWorker.connect.start",
                    url=self.url,
                    tickers=self.tickers,
                )

                async with aiohttp.ClientSession(
                    connector=_make_connector(),
                    headers=self.headers,
                ) as session:
                    async with session.ws_connect(self.url) as ws:
                        await self._subscribe(ws, self.tickers)
                        self._last_msg_ts = time.monotonic()

                        async def watchdog() -> None:
                            while True:
                                await asyncio.sleep(WATCHDOG_TIMEOUT_SECONDS)
                                if self._last_msg_ts is not None and (
                                    time.monotonic() - self._last_msg_ts > WATCHDOG_TIMEOUT_SECONDS
                                ):
                                    log.warning(
                                        "KalshiWSWorker.watchdog_timeout",
                                        timeout_seconds=WATCHDOG_TIMEOUT_SECONDS,
                                        tickers=self.tickers,
                                    )
                                    await ws.close(code=1000, message=b"watchdog timeout")
                                    break

                        async def periodic_reconnect() -> None:
                            await asyncio.sleep(PERIODIC_RECONNECT_SECONDS)
                            log.info(
                                "KalshiWSWorker.periodic_reconnect",
                                interval_seconds=PERIODIC_RECONNECT_SECONDS,
                                tickers=self.tickers,
                            )
                            await ws.close(code=1000, message=b"periodic reconnect")

                        watchdog_task = asyncio.create_task(watchdog())
                        reconnect_task = asyncio.create_task(periodic_reconnect())
                        dyn_task = asyncio.create_task(self._dynamic_subscribe_loop(ws))
                        try:
                            async for msg in ws:
                                if msg.type == WSMsgType.TEXT:
                                    self._last_msg_ts = time.monotonic()
                                    try:
                                        data = msg.json()
                                    except Exception as e:
                                        log.warning(
                                            "KalshiWSWorker.message.parse_failed",
                                            error=str(e),
                                            text=msg.data,
                                        )
                                        continue
                                    await self._handle_message(data)
                                elif msg.type == WSMsgType.ERROR:
                                    log.error(
                                        "KalshiWSWorker.ws_error",
                                        error=str(msg.data),
                                    )
                                    break
                        finally:
                            watchdog_task.cancel()
                            reconnect_task.cancel()
                            dyn_task.cancel()
                            for t in (watchdog_task, reconnect_task, dyn_task):
                                try:
                                    await t
                                except asyncio.CancelledError:
                                    pass

                delay = 1.0

            except Exception as e:
                log.error(
                    "KalshiWSWorker.connect.error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 60.0)


async def _test_run() -> None:
    """
    Тестовый запуск:
    - берём несколько активных тикеров из БД;
    - открываем одно WS‑соединение и подписываемся на них;
    - логируем входящие orderbook‑сообщения.
    """
    async with get_ro_session() as session:
        repo = KalshiRepository(session=session)
        tickers = await repo.get_active_tickers()

    if not tickers:
        log.warning("KalshiWSWorker.test: no active tickers found in DB")
        return

    sample = tickers
    log.info("KalshiWSWorker.test: using tickers", tickers=sample)

    updates_queue: asyncio.Queue = asyncio.Queue()
    worker = KalshiWSWorker(sample, updates_queue, asyncio.Queue())

    async def consumer():
        while True:
            ticker, kind, payload = await updates_queue.get()
            log.info(
                "KalshiWSWorker.test.message",
                ticker=ticker,
                kind=kind,
                payload=payload,
            )

    await asyncio.gather(worker.connect(), consumer())


if __name__ == "__main__":
    try:
        asyncio.run(_test_run())
    except KeyboardInterrupt:
        log.info("KalshiWSWorker.test: interrupted by user")
