import asyncpg
import structlog
from fastapi.exceptions import RequestValidationError
from fastapi import Request, HTTPException, FastAPI
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from starlette.responses import JSONResponse


logger = structlog.getLogger(__name__)


def _sanitize_for_json(obj):
    """Make obj JSON-serializable (replace bytes and other non-serializable)."""
    if isinstance(obj, bytes):
        return "<binary>"
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(x) for x in obj]
    return obj


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errors_safe = _sanitize_for_json(exc.errors())
    logger.warning(
        "Request validation failed",
        path=request.url.path,
        errors=errors_safe,
    )
    return JSONResponse(
        status_code=422,
        content={"detail": errors_safe},
    )


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
):
    logger.warning(
        "Database integrity error",
        path=request.url.path,
        error=str(exc.orig),
    )
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Database integrity constraint violated",
        },
    )


async def data_error_handler(
    request: Request,
    exc: DataError,
):
    logger.warning(
        "Database data error",
        path=request.url.path,
        error=str(exc.orig),
    )
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Invalid data format",
        },
    )


async def db_operational_error_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Database operational error",
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable",
        },
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    logger.info(
        "HTTP exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
        },
    )


def setup_exception_handlers(app: FastAPI):

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(DataError, data_error_handler)

    app.add_exception_handler(OperationalError, db_operational_error_handler)
    app.add_exception_handler(asyncpg.PostgresError, db_operational_error_handler)

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
