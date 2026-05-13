"""
Predict.fun WebSocket — подписка на orderbook по marketId.

Документация:
  https://dev.predict.fun/
  https://dev.predict.fun/get-the-orderbook-for-a-market-25326908e0 (REST orderbook)

Endpoint: wss://ws.predict.fun/ws

Топик: predictOrderbook/{marketId}
  Подписка: {"method": "subscribe", "requestId": int, "params": ["predictOrderbook/{marketId}"]}

Типы сообщений:
  - type "M" — push (orderbook update); topic = "predictOrderbook/{marketId}"
  - type "R" — ответ на subscribe
  - topic "heartbeat" — нужно ответить method "heartbeat", иначе соединение закроют (интервал ~15 сек)

Статусы: в документации явных событий «маркет закрыт» / «ордербук недоступен» по WS не описано.
"""
import asyncio
from typing import List, Optional, Dict, Any

import aiohttp
from aiohttp import WSMsgType
from aiohttp_socks import ProxyConnector
import structlog

from core.config import settings
from core.models.database import get_ro_session
from core.repositories.predictfun_repository import PredictfunRepository
from core.orderbook_formatters.predictfun_formatter import format_predictfun_orderbook


log = structlog.get_logger(__name__)


def _make_connector() -> Optional[ProxyConnector]:
    proxy_url = getattr(settings.predict_fun, "proxy_url", None)
    if proxy_url:
        return ProxyConnector.from_url(proxy_url)
    return None


class PredictfunWSWorker:
    """
    WebSocket‑клиент Predict.fun для подписки на orderbook сразу по нескольким marketId.

    Использует топики вида `predictOrderbook/{marketId}` на одном WS‑соединении.
    В продакшн‑режиме прокидывает нормализованные ордербуки в очередь обновлений.
    """

    def __init__(
        self,
        market_ids: List[str],
        updates_queue: asyncio.Queue,
        new_markets_queue: asyncio.Queue,
    ):
        self.market_ids: List[str] = list(market_ids)
        self.updates_queue = updates_queue
        self.new_markets_queue = new_markets_queue
        self.url = settings.predict_fun.ws_url
        self.api_key = settings.predict_fun.api_key
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse, market_ids: List[str]) -> None:
        if not market_ids:
            return
        for mid in market_ids:
            topic = f"predictOrderbook/{mid}"
            msg = {
                "method": "subscribe",
                "requestId": self._next_id(),
                "params": [topic],
            }
            await ws.send_json(msg)
            log.info("PredictfunWSWorker: subscribe sent", topic=topic)

    async def _dynamic_subscribe_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """Досылает subscribe для новых маркетов в уже открытое соединение."""
        while True:
            new_ids = await self.new_markets_queue.get()
            if not new_ids:
                continue
            try:
                await self._subscribe(ws, new_ids)
                self.market_ids.extend(new_ids)
            except Exception as e:
                log.error("PredictfunWSWorker: dynamic subscribe failed", error=str(e))
                await self.new_markets_queue.put(new_ids)
                return

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """
        Обработка входящих сообщений:
        - читаем topic вида `predictOrderbook/{marketId}`;
        - пробуем привести payload к формату format_predictfun_orderbook.
        """
        if data.get("type") != "M":
            # нас интересуют только message‑ивенты (heartbeat обрабатываем отдельно в connect)
            return

        topic = data.get("topic", "")
        if not topic.startswith("predictOrderbook/"):
            # может быть heartbeat или другие каналы
            return

        # topic: predictOrderbook/{marketId}
        try:
            _, market_id = topic.split("/", 1)
        except ValueError:
            log.warning("PredictfunWSWorker: unexpected topic format", topic=topic)
            return

        payload = data.get("data")
        if payload is None:
            log.debug("PredictfunWSWorker: empty data for topic", topic=topic)
            return

        # Нормализуем к уже существующему форматтеру
        wrapped = {"success": True, "data": payload}
        formatted = format_predictfun_orderbook(wrapped)
        if not formatted:
            return

        # Отдаём дальше в очередь для сервиса, чтобы тот отправил в Celery/БД
        await self.updates_queue.put((market_id, formatted))

    async def connect(self) -> None:
        """
        Открывает одно WS‑соединение и подписывается на несколько marketId.
        При обрыве — реконнект с экспоненциальной паузой.
        """
        delay = 1.0

        while True:
            try:
                log.info(
                    "PredictfunWSWorker.connect.start",
                    url=self.url,
                    market_ids=self.market_ids,
                )

                headers = {"x-api-key": self.api_key} if self.api_key else {}

                async with aiohttp.ClientSession(
                    connector=_make_connector(),
                    headers=headers,
                ) as session:
                    async with session.ws_connect(self.url) as ws:
                        await self._subscribe(ws, self.market_ids)

                        dyn_task = asyncio.create_task(self._dynamic_subscribe_loop(ws))
                        try:
                            async for msg in ws:
                                if msg.type == WSMsgType.TEXT:
                                    try:
                                        data = msg.json()
                                    except Exception as e:
                                        log.warning(
                                            "PredictfunWSWorker.message.parse_failed",
                                            error=str(e),
                                            text=msg.data,
                                        )
                                        continue

                                    if data.get("type") == "M" and data.get("topic") == "heartbeat":
                                        try:
                                            await ws.send_json(
                                                {
                                                    "method": "heartbeat",
                                                    "data": data.get("data"),
                                                }
                                            )
                                            log.debug("PredictfunWSWorker.heartbeat.sent")
                                        except Exception as e:
                                            log.warning(
                                                "PredictfunWSWorker.heartbeat.error",
                                                error=str(e),
                                            )
                                        continue

                                    await self._handle_message(data)
                                elif msg.type == WSMsgType.ERROR:
                                    log.error(
                                        "PredictfunWSWorker.ws_error",
                                        error=str(msg.data),
                                    )
                                    break
                        finally:
                            dyn_task.cancel()
                            try:
                                await dyn_task
                            except asyncio.CancelledError:
                                pass

                delay = 1.0

            except Exception as e:
                log.error(
                    "PredictfunWSWorker.connect.error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 60.0)


async def _test_run() -> None:
    """
    Тестовый запуск:
    - берём несколько активных predict_fun market_ids из БД (в парах);
    - открываем одно WS‑соединение с многими подписками;
    - логируем входящие orderbook‑сообщения.
    """
    async with get_ro_session() as session:
        repo = PredictfunRepository(session=session)
        market_ids = await repo.get_active_tickers_in_pairs()

    if not market_ids:
        log.warning("PredictfunWSWorker.test: no active market_ids found in DB")
        return

    sample = market_ids
    log.info("PredictfunWSWorker.test: using market_ids", market_ids=sample)

    updates_queue: asyncio.Queue = asyncio.Queue()
    worker = PredictfunWSWorker(sample, updates_queue, asyncio.Queue())

    async def consumer():
        while True:
            market_id, ob = await updates_queue.get()
            log.info(
                "PredictfunWSWorker.test.message",
                market_id=market_id,
                orderbook=ob,
            )

    await asyncio.gather(worker.connect(), consumer())


if __name__ == "__main__":
    # Пример запуска:
    #   docker exec -it update_orderbooks_service python -m orderbook_service.predictfun_ws
    try:
        asyncio.run(_test_run())
    except KeyboardInterrupt:
        log.info("PredictfunWSWorker.test: interrupted by user")

