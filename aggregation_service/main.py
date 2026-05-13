import logging
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

from api.arbitrage import router as arbitrage_router
from api.markets import router as markets_router
from core.exc.async_exc_handler import setup_asyncio_exception_handler
from core.exc.fastapi_exc_handler import setup_exception_handlers
from core.middleware.rate_limit import RateLimitMiddleware
from core.observe.sentry import setup_sentry
from core.redis.redis_cli import RedisService

logger = structlog.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_sentry()
    setup_asyncio_exception_handler()

    redis_url = settings.redis.sync_url or "redis://localhost:6378/0"
    redis_service = RedisService(redis_url)

    try:
        await redis_service.connect()
        app.state.redis_service = redis_service
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.critical(
            "Failed to connect to Redis on startup. Aborting application launch.",
            error=str(e),
            exc_info=True,
        )
        raise RuntimeError("Redis connection failed. Application cannot start.") from e

    try:
        yield
    finally:
        await redis_service.close()
        logger.info("Shutdown complete")


app = FastAPI(title="Arbitrage Engine", lifespan=lifespan)

if settings.rate_limit.enabled:
    app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_exception_handlers(app)

app.include_router(markets_router)
app.include_router(arbitrage_router)


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=settings.uvicorn_workers,
    )
