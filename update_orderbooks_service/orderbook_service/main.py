import asyncio
import logging
import sys
from pathlib import Path

import sentry_sdk
import structlog
from sentry_sdk.integrations.asyncio import AsyncioIntegration

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.CallsiteParameterAdder([
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.FUNC_NAME,
            structlog.processors.CallsiteParameter.LINENO,
        ]),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


from core.config import settings
from core.models.database import get_ro_session

logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
from core.repositories.poly_repository import PolymarketRepository
from orderbook_service.kalshi.ws_service import KalshiWSService
from orderbook_service.polymarket.ws import WSManager
from orderbook_service.predictfun.ws_service import PredictfunWSService

log = structlog.get_logger(__name__)


def _init_sentry() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        integrations=[AsyncioIntegration()],
        traces_sample_rate=0.0,
    )
    log.info("Sentry initialized", environment=settings.env)


_init_sentry()


RESTART_DELAY = 5


class OrderbookServicesManager:

    def __init__(self):
        self.kalshi_service: KalshiWSService | None = None
        self.predictfun_service: PredictfunWSService | None = None
        self.polymarket_manager: WSManager | None = None
        self._shutdown_event = asyncio.Event()

    async def run_kalshi_service(self):
        while not self._shutdown_event.is_set():
            try:
                self.kalshi_service = KalshiWSService()
                await self.kalshi_service.run()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("Kalshi service crashed, restarting", error=str(e), exc_info=True)
                await asyncio.sleep(RESTART_DELAY)

    async def run_predictfun_service(self):
        while not self._shutdown_event.is_set():
            try:
                self.predictfun_service = PredictfunWSService()
                await self.predictfun_service.run()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("PredictFun service crashed, restarting", error=str(e), exc_info=True)
                await asyncio.sleep(RESTART_DELAY)

    async def run_polymarket_service(self):
        while not self._shutdown_event.is_set():
            try:
                async with get_ro_session() as session:
                    repository = PolymarketRepository(session=session)
                    self.polymarket_manager = WSManager(repository)
                    await self.polymarket_manager.run()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("Polymarket service crashed, restarting", error=str(e), exc_info=True)
                await asyncio.sleep(RESTART_DELAY)

    async def run_all(self):
        log.info("Starting all orderbook services")
        await asyncio.gather(
            self.run_kalshi_service(),
            self.run_predictfun_service(),
            self.run_polymarket_service(),
        )

    async def shutdown(self):
        log.info("Shutting down all orderbook services")
        self._shutdown_event.set()

        # Останавливаем polling сервисы
        if self.kalshi_service:
            try:
                await self.kalshi_service.stop()
            except Exception as e:
                log.error(
                    "Error stopping Kalshi services",
                    error=str(e),
                    exc_info=True,
                )

        if self.predictfun_service:
            try:
                await self.predictfun_service.stop()
            except Exception as e:
                log.error(
                    "Error stopping Predict.fun services",
                    error=str(e),
                    exc_info=True,
                )

        if self.polymarket_manager:
            try:
                await self.polymarket_manager.stop()
            except Exception as e:
                log.error(
                    "Error stopping Polymarket services",
                    error=str(e),
                    exc_info=True,
                )

        log.info("All services stopped")


async def main():
    manager = OrderbookServicesManager()
    try:
        await manager.run_all()
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    log.info("Starting orderbook services manager")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception as e:
        log.error(
            "Failed to start services",
            error=str(e),
            exc_info=True,
        )
        sys.exit(1)

