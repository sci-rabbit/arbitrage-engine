from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

logger = structlog.get_logger(__name__)


engine = create_async_engine(
    url=settings.db.url,
    echo=settings.db.echo,
    echo_pool=settings.db.echo_pool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
)


async def dispose() -> None:
    await engine.dispose()


async_session = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_rw_session() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(
                "Error in read-write session",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise


async def get_ro_session() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(
                "Error in read-only session",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
