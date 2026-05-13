import asyncio
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from redis.asyncio import from_url as redis_from_url
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sqlalchemy.exc import IntegrityError, OperationalError

from api.routes.admin import router as admin_router
from api.routes.auth import router as auth_router
from api.routes.payments import router as payments_router
from api.routes.subscriptions import router as subscriptions_router
from api.routes.transactions import router as transactions_router
from api.routes.users import router as users_router
from core.config import settings
from core.database import dispose
from exceptions.base import BaseAppException

logger = structlog.get_logger(__name__)


def init_sentry() -> None:
    if not settings.sentry.enabled or not settings.sentry.dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry.dsn,
        environment=settings.sentry.environment,
        traces_sample_rate=settings.sentry.traces_sample_rate,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
    )


def handle_asyncio_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    exc = context.get("exception")
    message = context.get("message", "Unknown asyncio error")

    if exc:
        sentry_sdk.capture_exception(exc)
        logger.error("Unhandled asyncio exception", message=message, exc_info=exc)
    else:
        logger.error("Asyncio error without exception", message=message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_asyncio_exception)
    redis = redis_from_url(settings.redis.url, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)
    logger.info("Application started")
    yield
    await dispose()
    await FastAPILimiter.close()
    logger.info("Application stopped")


def create_app() -> FastAPI:
    init_sentry()

    app = FastAPI(
        title=settings.app.title,
        version=settings.app.version,
        debug=settings.app.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
    )

    # --- Exception handlers ---

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Невалидные входные данные — 422, не логируем, не шлём в Sentry
        # In Pydantic v2 ctx.error may hold a ValueError object → not JSON serializable
        errors = []
        for err in exc.errors():
            if "ctx" in err and isinstance(err["ctx"].get("error"), Exception):
                err = {**err, "ctx": {**err["ctx"], "error": str(err["ctx"]["error"])}}
            errors.append(err)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": errors},
        )

    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
        # Бизнес-исключения (NotFound, AlreadyExists, NotEnoughBalance…)
        # Ожидаемые ошибки — warning, не шлём в Sentry
        logger.warning(
            "Business exception",
            path=request.url.path,
            detail=exc.detail,
            status_code=exc.status_code,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        # Нарушение constraint БД которое не поймали в сервисе — 409
        # Не шлём в Sentry — это data-ошибка, не баг
        logger.warning(
            "Database integrity error",
            path=request.url.path,
            error=str(exc.orig),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Resource conflict"},
        )

    @app.exception_handler(OperationalError)
    async def db_operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
        # БД недоступна или таймаут — 503, шлём в Sentry
        sentry_sdk.capture_exception(exc)
        logger.error(
            "Database operational error",
            path=request.url.path,
            error=str(exc.orig),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service temporarily unavailable"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        sentry_sdk.capture_exception(exc)
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # --- Health check ---

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}

    # --- Routers ---

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(subscriptions_router)
    app.include_router(transactions_router)
    app.include_router(payments_router)
    app.include_router(admin_router)

    return app

app = create_app()

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
