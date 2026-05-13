"""
Воркер арбитража — отдельный процесс. Свой Redis-клиент и пул, не конкурирует с API за event loop.
Запуск: python run_arbitrage_worker.py
"""
import asyncio
import logging
import signal
import sys

import structlog

from core.config import settings
from core.observe.sentry import setup_sentry
from core.redis.redis_cli import RedisService
from arbitrage_task import ArbitrageTask

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
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
setup_sentry()

logger = structlog.get_logger(__name__)

async def run_worker() -> None:
    redis_url = settings.redis.sync_url or "redis://localhost:6378/0"
    redis_service = RedisService(redis_url)

    try:
        await redis_service.connect()
        logger.info("Arbitrage worker: Redis connected")
    except Exception as e:
        logger.critical("Arbitrage worker: Redis connection failed", error=str(e), exc_info=True)
        raise RuntimeError("Redis connection failed.") from e

    arb_task = ArbitrageTask(redis_service=redis_service)
    task_handle = asyncio.create_task(arb_task.run_forever(interval=settings.arbitrage.scan_interval))

    shutdown_event = asyncio.Event()

    def _on_signal(*_args):
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _on_signal)
        except (ValueError, OSError):
            pass

    try:
        await shutdown_event.wait()
    except asyncio.CancelledError:
        pass
    finally:
        task_handle.cancel()
        try:
            await task_handle
        except asyncio.CancelledError:
            pass
        arb_task.executor.shutdown(wait=True)
        await redis_service.close()
        logger.info("Arbitrage worker: shutdown complete")


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
