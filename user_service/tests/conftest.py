"""
Test infrastructure for user_service.

DB isolation  — каждый тест оборачивается в транзакцию с роллбэком.
Rate limiting — RateLimiter.__call__ заменён no-op (autouse).
Redis         — lifespan получает fakeredis вместо реального Redis.
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import patch

import fakeredis.aioredis
from fastapi import Request
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.pool import StaticPool
from starlette.responses import Response as StarletteResponse

import models  # noqa: F401— регистрирует все модели в Base.metadata
from main import app
from core.database import get_rw_session, get_ro_session
from models.base import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# db — каждый тест получает свой in-memory движок → полная изоляция
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    _engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    conn = await _engine.connect()
    tx = await conn.begin()

    session_factory = async_sessionmaker(
        bind=conn,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    await tx.rollback()
    await conn.close()
    await _engine.dispose()


# ---------------------------------------------------------------------------
# Rate limiter — отключаем для всех тестов
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    """Глушим отправку email во всех тестах."""
    from unittest.mock import AsyncMock
    monkeypatch.setattr("api.routes.auth.send_verification_email", AsyncMock())
    monkeypatch.setattr("api.routes.auth.send_reset_password_email", AsyncMock())


@pytest.fixture(autouse=True)
def disable_rate_limit(monkeypatch):
    async def _no_op(self, request: Request, response: StarletteResponse):
        pass
    monkeypatch.setattr("fastapi_limiter.depends.RateLimiter.__call__", _no_op)


@pytest.fixture(autouse=True)
def patch_for_update(monkeypatch):
    """SQLite не поддерживает WITH FOR UPDATE — убираем блокировку."""
    from sqlalchemy import select
    from repositrories.user_repository import UserRepository
    from repositrories.user_subscription_repository import UserSubscriptionRepository
    from models.user_subscriptions import UserSubscription

    async def _get_user(self, user_id: int):
        return await self.get(user_id)

    async def _get_sub_active(self, user_id, subscription_id, now):
        stmt = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.expired_at > now,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_user_and_sub(self, user_id, subscription_id):
        stmt = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    monkeypatch.setattr(UserRepository, "get_for_update", _get_user)
    monkeypatch.setattr(UserSubscriptionRepository, "get_active", _get_sub_active)
    monkeypatch.setattr(UserSubscriptionRepository, "get_by_user_and_subscription", _get_by_user_and_sub)


# ---------------------------------------------------------------------------
# client — AsyncClient с подменой сессий и fakeredis в lifespan
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _rw():
        yield db

    async def _ro():
        yield db

    app.dependency_overrides[get_rw_session] = _rw
    app.dependency_overrides[get_ro_session] = _ro

    fake_redis = fakeredis.aioredis.FakeRedis()
    with patch("main.redis_from_url", return_value=fake_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()