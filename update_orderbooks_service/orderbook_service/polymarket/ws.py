import asyncio
import time

import aiohttp
import structlog
from typing import List, Dict, Tuple

from aiohttp_socks import ProxyConnector


from core.config import settings
from core.models.database import get_ro_session
from core.models.database import get_rw_session
from core.repositories.orderbook_repository import OrderbookAsyncRepository
from core.repositories.poly_repository import PolymarketRepository


log = structlog.get_logger(__name__)


def _make_connector() -> ProxyConnector | None:
    proxy_url = getattr(settings.polymarket, "proxy_url", None)
    if proxy_url:
        return ProxyConnector.from_url(proxy_url)
    return None

WATCHDOG_TIMEOUT_SECONDS = 60
PERIODIC_RECONNECT_SECONDS = 600  # принудительный реконнект каждые 10 минут для свежего initial_dump


class PolymarketWSWorker:
    def __init__(
        self,
        asset_ids: List[str],
        updates_queue: asyncio.Queue,
        market_map: Dict[str, Tuple[str, str]],
    ):
        self.asset_ids = asset_ids
        self.updates_queue = updates_queue
        self.market_map = market_map
        self.orderbooks = {aid: {"bids": [], "asks": []} for aid in asset_ids}
        self.url = settings.polymarket.order_book_url
        self._last_msg_ts: float | None = None
        self._stop_event = asyncio.Event()

    async def stop(self) -> None:
        self._stop_event.set()

    async def connect(self):
        delay = 1
        while not self._stop_event.is_set():
            try:
                async with aiohttp.ClientSession(connector=_make_connector()) as session:
                    async with session.ws_connect(self.url) as ws:
                        await self._subscribe(ws)
                        # инициализируем watchdog: считаем, что после подписки должны прийти данные
                        self._last_msg_ts = time.monotonic()

                        async def watchdog() -> None:
                            while True:
                                await asyncio.sleep(WATCHDOG_TIMEOUT_SECONDS)
                                if self._last_msg_ts is None:
                                    continue
                                if time.monotonic() - self._last_msg_ts > WATCHDOG_TIMEOUT_SECONDS:
                                    log.warning(
                                        "PolymarketWSWorker.watchdog_timeout",
                                        timeout_seconds=WATCHDOG_TIMEOUT_SECONDS,
                                        asset_count=len(self.asset_ids),
                                    )
                                    # Закрываем WS; это выведет нас из цикла и запустит реконнект
                                    await ws.close(code=1000, message=b"watchdog timeout")
                                    break

                        connect_ts = time.monotonic()

                        async def periodic_reconnect() -> None:
                            await asyncio.sleep(PERIODIC_RECONNECT_SECONDS)
                            log.info(
                                "PolymarketWSWorker.periodic_reconnect",
                                interval_seconds=PERIODIC_RECONNECT_SECONDS,
                                asset_count=len(self.asset_ids),
                            )
                            await ws.close(code=1000, message=b"periodic reconnect")

                        watchdog_task = asyncio.create_task(watchdog())
                        reconnect_task = asyncio.create_task(periodic_reconnect())
                        try:
                            async for msg in ws:
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    self._last_msg_ts = time.monotonic()
                                    data = msg.json()
                                    await self._handle_message(data)
                                elif msg.type == aiohttp.WSMsgType.ERROR:
                                    log.error("WS error", msg=msg.data)
                                    break
                        finally:
                            watchdog_task.cancel()
                            reconnect_task.cancel()
                            for t in (watchdog_task, reconnect_task):
                                try:
                                    await t
                                except asyncio.CancelledError:
                                    pass
                delay = 1
            except Exception as e:
                log.error(
                    "WebSocket failed, reconnecting",
                    exception=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 60)

    async def _subscribe(self, ws):
        subscribe_msg = {
            "type": "market",
            "assets_ids": self.asset_ids,
            "initial_dump": True,
        }
        await ws.send_json(subscribe_msg)
        log.info("Subscribed to assets", assets=self.asset_ids)

    async def _handle_message(self, data):
        if isinstance(data, list):
            for item in data:
                await self._handle_message(item)
            return

        asset_id = data.get("asset_id")
        if not asset_id or asset_id not in self.orderbooks:
            return

        if "bids" in data and data["bids"]:
            self.orderbooks[asset_id]["bids"] = data["bids"]

        if "asks" in data and data["asks"]:
            self.orderbooks[asset_id]["asks"] = data["asks"]

        asset_info = self.market_map.get(asset_id)
        if not asset_info:
            log.error("Asset info not found", asset_id=asset_id)
            return
        market_id, side = asset_info
        if not market_id or not side:
            log.error("Market ID or side not found", asset_id=asset_id)
            return
        orderbook = self.orderbooks[asset_id]
        if not orderbook:
            return
        log.info(
            "Orderbook updated", market_id=market_id, side=side, orderbook=orderbook
        )
        log.info(
            "Putting orderbook into queue",
            market_id=market_id,
            side=side,
            orderbook=orderbook,
        )
        await self.updates_queue.put((market_id, side, orderbook))


class MarketFetcher:
    def __init__(self, market_repository):
        self.market_repository = market_repository

    async def fetch_asset_ids(self) -> List[str]:
        markets = await self.market_repository.get_active_markets()
        return [m.asset_id for m in markets if m.asset_id]


class WSManager:
    def __init__(self, market_repository):
        self.market_repository = market_repository
        self.updates_queue = asyncio.Queue(maxsize=settings.ws_worker.UPDATES_QUEUE_MAX_SIZE)
        self.market_map = {}
        self.market_orderbooks = {}
        self.workers: List[PolymarketWSWorker] = []
        self._stop_event = asyncio.Event()

    async def stop(self) -> None:
        self._stop_event.set()
        for worker in self.workers:
            await worker.stop()

    async def load_mapping(self) -> None:
        log.info("Loading market mapping from database")
        self.market_map = await self.market_repository.get_token_ids_and_market_id()
        log.info("Market mapping loaded", count=len(self.market_map))
        self.market_orderbooks = {}
        for asset_id, (market_id, side) in self.market_map.items():
            self.market_orderbooks.setdefault(market_id, {"yes": None, "no": None})
        log.info("Market orderbooks initialized", count=len(self.market_orderbooks))

    async def stop_inactive_workers(self, new_market_map):
        new_market_ids = {m_id for (m_id, _) in new_market_map.values()}

        active_workers = []
        for worker in self.workers:
            worker_market_ids = {
                self.market_map[asset_id][0]
                for asset_id in worker.asset_ids
                if asset_id in self.market_map
            }

            if worker_market_ids.isdisjoint(new_market_ids):
                await worker.stop()
            else:
                active_workers.append(worker)

        self.workers = active_workers

    async def add_new_workers(self):
        """
        Добавить workers для новых asset_ids, которых еще нет в существующих workers.
        """
        # Получаем актуальный mapping
        new_market_map = await self.market_repository.get_token_ids_and_market_id()

        await self.stop_inactive_workers(new_market_map)
        # Обновляем market_map (сохраняем ссылку для существующих workers)
        self.market_map.clear()
        self.market_map.update(new_market_map)

        # Обновляем market_orderbooks для новых маркетов
        for asset_id, (market_id, side) in new_market_map.items():
            if market_id not in self.market_orderbooks:
                self.market_orderbooks[market_id] = {"yes": None, "no": None}

        # Собираем все asset_ids, которые уже обрабатываются существующими workers
        existing_asset_ids = set()
        for worker in self.workers:
            existing_asset_ids.update(worker.asset_ids)

        # Находим новые asset_ids
        all_asset_ids = set(new_market_map.keys())
        new_asset_ids = all_asset_ids - existing_asset_ids

        if not new_asset_ids:
            log.debug("No new asset_ids to add")
            return

        log.info(
            "Adding workers for new markets",
            new_count=len(new_asset_ids),
            existing_count=len(existing_asset_ids),
            total_count=len(all_asset_ids),
        )

        # Разбиваем новые asset_ids на батчи
        new_asset_ids_list = list(new_asset_ids)
        batches = [
            new_asset_ids_list[i : i + settings.ws_worker.BATCH_SIZE]
            for i in range(0, len(new_asset_ids_list), settings.ws_worker.BATCH_SIZE)
        ]

        # Создаем новых workers для новых батчей
        new_workers = [
            PolymarketWSWorker(batch, self.updates_queue, dict(self.market_map))
            for batch in batches
        ]

        # Добавляем в список активных workers
        self.workers.extend(new_workers)

        # Запускаем новых workers в фоне (не блокируем основной поток)
        for worker in new_workers:
            asyncio.create_task(worker.connect())

    async def _refresh_markets_loop(self):
        """
        Периодическое обновление списка активных маркетов и добавление workers для новых.
        """
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(settings.ws_worker.MARKETS_REFRESH_INTERVAL)
                await self.add_new_workers()
            except Exception as e:
                log.error(
                    "Error in refresh markets loop",
                    error=str(e),
                    exc_info=True,
                )

    async def run(self):
        log.info("WSManager.run() started")
        await self.load_mapping()

        asset_ids = list(self.market_map.keys())
        log.info("Asset IDs collected", count=len(asset_ids))

        if not asset_ids:
            log.warning("No asset IDs found, waiting for markets")

        batches = [
            asset_ids[i : i + settings.ws_worker.BATCH_SIZE]
            for i in range(0, len(asset_ids), settings.ws_worker.BATCH_SIZE)
        ]
        self.workers = [
            PolymarketWSWorker(batch, self.updates_queue, dict(self.market_map))
            for batch in batches
        ]
        log.info("Workers created", worker_count=len(self.workers))

        await asyncio.gather(
            self._batch_updater(),
            self._refresh_markets_loop(),
            *(w.connect() for w in self.workers),
        )

    async def _batch_updater(self):
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(settings.ws_worker.UPDATE_INTERVAL)

                while not self.updates_queue.empty():
                    market_id, side, orderbook = await self.updates_queue.get()
                    # защитимся от KeyError, если пришёл маркет, которого ещё нет в словаре
                    self.market_orderbooks.setdefault(
                        market_id, {"yes": None, "no": None}
                    )[side] = orderbook

                update_batch = {
                    mid: ob
                    for mid, ob in self.market_orderbooks.items()
                    # отправляем маркет, если обновилась хотя бы одна сторона стакана;
                    # в репозитории частичным обновлением старая сторона сохранится
                    if ob.get("yes") is not None or ob.get("no") is not None
                }

                if update_batch:
                    async with get_rw_session() as session:
                        repo = OrderbookAsyncRepository(session)
                        for mid, ob in update_batch.items():
                            await repo.upsert_orderbook(mid, ob)
            except Exception as e:
                log.error(
                    "Error in batch_updater",
                    error=str(e),
                    exc_info=True,
                )


async def main():
    log.info("Starting Polymarket WebSocket services")
    try:
        log.info("Getting database session...")
        async with get_ro_session() as session:
            log.info("Database session obtained")
            repository = PolymarketRepository(session=session)
            log.info("PolymarketRepository created")
            manager = WSManager(repository)
            log.info("WSManager created, starting run()")
            await manager.run()
    except Exception as e:
        log.exception("Fatal error in main", error=str(e), exc_info=True)
        raise