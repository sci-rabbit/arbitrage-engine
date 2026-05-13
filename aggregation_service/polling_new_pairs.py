import asyncio
import logging
import sys

import sentry_sdk
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

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

from core.models.database import context_manager_get_ro_session
from core.repositories.invalid_pairs_repository import InvalidPairRepository
from core.repositories.market_repository import MarketRepository
from services.pair_generation_service.service import PairGenerationService
from services.similarity_service.channels.semantic import SemanticChannel
from services.similarity_service.channels.title import TitleChannel
from services.similarity_service.service import MarketSimilarityService

logger = structlog.getLogger(__name__)


class PairPollingService:
    def __init__(self, pair_generation_service: PairGenerationService, session: AsyncSession):
        self.pair_generation_service = pair_generation_service
        self.session = session
        self.running = False

    async def start_polling(self, limit: int = 60000):
        """
        Бесконечный цикл опроса для генерации новых пар.
        """
        self.running = True
        offset = 0

        while self.running:
            try:
                saved_count = await self.pair_generation_service.generate_and_store(
                    limit=limit,
                    offset=offset,
                )
                logger.info("Polling batch finished", saved=saved_count)
                # Если пары закончились, сбрасываем offset
                offset = offset + limit if saved_count > 0 else 0
            except Exception as e:
                logger.exception("Error during pair polling", error=str(e))
                try:
                    await self.session.rollback()
                except Exception:
                    pass

            await asyncio.sleep(settings.pair_polling.poll_interval)

    async def stop_polling(self):
        self.running = False


def init_polling_service(session: AsyncSession):
    market_repository = MarketRepository(session=session)
    invalid_pair_repository = InvalidPairRepository(session=session)

    cfg = settings.pair_polling
    market_similarity_service = MarketSimilarityService(
        repo=market_repository,
        channels=[TitleChannel(), SemanticChannel()],
        threshold=cfg.similarity_threshold,
        max_distance=cfg.max_distance,
    )
    market_generation_service = PairGenerationService(
        similarity_service=market_similarity_service,
        market_repo=market_repository,
        invalid_pair_repo=invalid_pair_repository,
    )
    polling_service = PairPollingService(
        pair_generation_service=market_generation_service,
        session=session,
    )
    return polling_service


async def polling_worker(polling_service: PairPollingService):
    while True:
        try:
            await polling_service.start_polling(limit=settings.pair_polling.batch_limit)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(
                "Polling task crashed, restarting", error=str(e), exc_info=True
            )
            await asyncio.sleep(settings.pair_polling.restart_delay)



async def pair_polling_run():
    while True:
        try:
            async with context_manager_get_ro_session() as session:
                polling_service = init_polling_service(session=session)
                await polling_worker(polling_service=polling_service)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception("Polling bootstrap crashed, restarting", error=str(e))
            await asyncio.sleep(settings.pair_polling.restart_delay)


if __name__ == "__main__":
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
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    from core.observe.sentry import setup_sentry
    setup_sentry()

    asyncio.run(pair_polling_run())
