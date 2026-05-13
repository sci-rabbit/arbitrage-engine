import asyncio
import logging
import sys

import sentry_sdk
import structlog
from sentry_sdk.integrations.asyncio import AsyncioIntegration

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(message)s",
)

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

logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

from core.models.database import get_ro_session
from core.repositories.health_repository import HealthRepository
from services.kalshi_markets_loader import KalshiPollingService
from services.polymarket_markets_loader import PolymarketPollingService
from services.predict_fun_markets_loader import PredictFunPollingService

logger = structlog.getLogger(__name__)


def _init_sentry() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        integrations=[AsyncioIntegration()],
        traces_sample_rate=0.0,
    )
    logger.info("Sentry initialized", environment=settings.env)


_init_sentry()


async def run_filler():
    async with get_ro_session() as session:
        health_repo = HealthRepository(session=session)
        is_db_online = await health_repo.is_database_online()
        if not is_db_online:
            logger.critical("Database is not online. Aborting markets loading.")
            return

    logger.info("Database healthcheck passed. Proceeding with loaders.")

    logger.info("Start markets loading")

    loaders = [
        PolymarketPollingService,
        PredictFunPollingService,
        KalshiPollingService,
    ]
    tasks = [asyncio.create_task(loader.run()) for loader in loaders]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Loading markets failed", error=str(result), exc_info=True)
        else:
            logger.info(
                "Loading markets finished for services",
                service_name=loaders[i].__name__,
                result=result,
            )
    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.warning(
                    "Task was cancelled",
                    service_name=loaders[tasks.index(task)].__name__,
                )


if __name__ == "__main__":

    asyncio.run(run_filler())
