from typing import Optional

import redis.asyncio as redis
import structlog
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    RedisError,
)

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

logger = structlog.getLogger(__name__)


RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
)


class RedisService:
    def __init__(
        self,
        url: str,
        *,
        max_connections: int = 100,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        health_check_interval: int = 30,
    ):
        self._url = url
        self._redis: Optional[redis.Redis] = None

        self._pool = redis.ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            health_check_interval=health_check_interval,
            decode_responses=False,
        )

    async def connect(self) -> None:
        self._redis = redis.Redis(connection_pool=self._pool)
        await self._ping()

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
        await self._pool.disconnect()

    async def _ping(self) -> None:
        if not self._redis:
            raise RuntimeError("Redis not initialized")
        await self._redis.ping()

    def _client(self) -> redis.Redis:
        if not self._redis:
            raise RuntimeError("RedisService not connected")
        return self._redis

    # ==============================
    # Retry wrapper
    # ==============================

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.2, max=5),
        reraise=True,
    )
    async def get(self, key: str) -> Optional[bytes]:
        return await self._client().get(key)

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.2, max=5),
        reraise=True,
    )
    async def set(
        self,
        key: str,
        value: bytes,
        *,
        ex: Optional[int] = None,
    ) -> bool:
        return await self._client().set(key, value, ex=ex)

    @retry(
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.2, max=5),
        reraise=True,
    )
    async def delete(self, key: str) -> int:
        return await self._client().delete(key)

    # ==============================
    # Advanced
    # ==============================

    async def pipeline(self):
        return self._client().pipeline(transaction=True)

    async def health(self) -> bool:
        try:
            await self._ping()
            return True
        except RedisError:
            return False
