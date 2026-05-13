from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from contextlib import contextmanager

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


@asynccontextmanager
async def get_rw_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_ro_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Read-only database session context manager.
    Properly handles errors and ensures session is closed even on exceptions.
    """
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
            # For read-only sessions, we don't need rollback
            # The async context manager will ensure session is closed
            raise


@asynccontextmanager
async def context_manager_get_ro_session():
    """
    Alternative name for get_ro_session for backward compatibility.
    Properly handles errors and ensures session is closed even on exceptions.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(
                "Error in read-only session (context_manager)",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

# Sync database

sync_engine = create_engine(
    url=settings.db.sync_url,
    echo=settings.db.echo,
    echo_pool=settings.db.echo_pool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
)

sync_session = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def get_sync_ro_session() -> Session:
    session = sync_session()
    try:
        yield session
    except Exception as e:
        logger.error(
            "Error in sync read-only session",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
    finally:
        session.close()


@contextmanager
def get_sync_rw_session() -> Session:
    with sync_session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
