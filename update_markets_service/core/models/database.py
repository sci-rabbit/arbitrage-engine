from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

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


@asynccontextmanager
async def get_rw_session() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_ro_session() -> AsyncGenerator[AsyncSession, Any]:
    async with async_session() as session:
        yield session
