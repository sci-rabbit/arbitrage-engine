import asyncio
import logging
import aiohttp
import structlog
import sys


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
from core.repositories.market_repository import MarketRepository
from core.markets_embedding.embedding_client import EmbeddingClient
from core.market_parsers.semantic import build_semantic_text

logger = structlog.getLogger(__name__)

BATCH_SIZE = settings.embedding.batch_size
MAX_CONCURRENCY = settings.embedding.max_concurrency
POLL_INTERVAL = settings.embedding.poll_interval


async def process_market(market, aio_session, semaphore):
    async with semaphore:
        try:
            texts: list[tuple[str, str]] = []   

            if market.embedding is None and market.normalized_title:
                texts.append(("title", market.normalized_title))

            if market.semantic_embedding is None:
                try:
                    semantic = market.semantic_text or build_semantic_text(
                        market=market
                    )
                    market.semantic_text = semantic
                    texts.append(("semantic", semantic))
                except Exception as e:
                    logger.exception(
                        "Failed to build semantic text",
                        market_id=market.platform_market_id,
                        error=str(e),
                        exc_info=True,
                    )
                    return

            if not texts:
                return

            logger.debug(
                "Embedding requested",
                market_id=market.platform_market_id,
                types=[k for k, _ in texts],
            )

            emb_client = EmbeddingClient(
                texts=[text for _, text in texts],
                aio_session=aio_session,
            )

            try:
                embeddings = await emb_client.get_embeddings()
            except Exception as e:
                logger.exception(
                    "Embedding services call failed",
                    market_id=market.platform_market_id,
                    error=str(e),
                    exc_info=True,
                )
                return

            if not embeddings or len(embeddings) != len(texts):
                logger.error(
                    "Embedding count mismatch",
                    market_id=market.platform_market_id,
                    expected=len(texts),
                    got=len(embeddings) if embeddings else 0,
                )
                return

            for (key, _), emb in zip(texts, embeddings):
                if emb is None:
                    logger.warning(
                        "Received None embedding",
                        market_id=market.platform_market_id,
                        embedding_type=key,
                    )
                    continue

                if key == "title":
                    market.embedding = emb
                elif key == "semantic":
                    market.semantic_embedding = emb

            logger.debug(
                "Embedding updated",
                market_id=market.platform_market_id,
                updated=[k for k, _ in texts],
            )

        except Exception as e:
            logger.exception(
                "Unexpected error while processing market",
                market_id=getattr(market, "platform_market_id", None),
                error=str(e),
                exc_info=True,
            )


async def run_once():
    logger.info("Embedding backfill iteration started")

    async with get_ro_session() as db_session:
        repo = MarketRepository(session=db_session)
        markets = await repo.get_with_none_emb()

        logger.info("Markets loaded", count=len(markets))

        semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

        async with aiohttp.ClientSession() as aio_session:
            for i in range(0, len(markets), BATCH_SIZE):
                batch = markets[i : i + BATCH_SIZE]

                await asyncio.gather(
                    *[process_market(m, aio_session, semaphore) for m in batch]
                )

                await db_session.commit()

    logger.info("Embedding backfill iteration finished")


async def main():
    logger.info("Embedding backfill loop started", poll_interval=POLL_INTERVAL)
    while True:
        try:
            await run_once()
        except Exception as e:
            logger.exception(
                "Embedding backfill iteration failed",
                error=str(e),
                exc_info=True,
            )
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
