import json
import time

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self.requests_per_minute = settings.rate_limit.requests_per_minute
        self.requests_per_hour = settings.rate_limit.requests_per_hour
        self.trusted_origins: set[str] = set(settings.rate_limit.trusted_origins)

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit.enabled:
            return await call_next(request)

        if request.url.path == "/healthcheck":
            return await call_next(request)

        origin = request.headers.get("origin", "") or request.headers.get("referer", "")
        if origin and any(origin.startswith(t) for t in self.trusted_origins):
            return await call_next(request)

        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client_ip = forwarded_for or request.headers.get("x-real-ip", "") or (request.client.host if request.client else "unknown")

        try:
            redis_service = request.app.state.redis_service
            allowed, reason = await self._check_redis(redis_service, client_ip)
        except Exception as e:
            logger.warning("rate_limit_redis_unavailable", error=str(e))
            return await call_next(request)

        if not allowed:
            return Response(
                content=json.dumps({"detail": f"Rate limit exceeded ({reason})."}),
                status_code=429,
                media_type="application/json",
            )

        return await call_next(request)

    async def _check_redis(self, redis_service, client_ip: str) -> tuple[bool, str]:
        now = int(time.time())
        minute_key = f"rl:{client_ip}:m:{now // 60}"
        hour_key = f"rl:{client_ip}:h:{now // 3600}"

        pipe = await redis_service.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        results = await pipe.execute()

        minute_count: int = results[0]
        hour_count: int = results[2]

        if minute_count > self.requests_per_minute:
            logger.warning("rate_limit_exceeded", client_ip=client_ip, window="minute", count=minute_count)
            return False, "minute"
        if hour_count > self.requests_per_hour:
            logger.warning("rate_limit_exceeded", client_ip=client_ip, window="hour", count=hour_count)
            return False, "hour"

        return True, ""
