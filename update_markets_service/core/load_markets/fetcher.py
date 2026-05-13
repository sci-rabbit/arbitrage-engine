import asyncio
from typing import Dict, Any, List

import aiohttp
from aiohttp import ClientTimeout, ClientResponseError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

Json = Dict[str, Any] | List[Dict[str, Any]] | List[Any]


class RateLimitError(Exception):
    """HTTP 429 — caller exceeded rate limit, safe to retry after backoff."""


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (
        aiohttp.ClientConnectorError,
        aiohttp.ServerTimeoutError,
        asyncio.TimeoutError,
        RateLimitError,
    )):
        return True
    # 5xx — server-side, safe to retry; 4xx (except 429) — client error, do not retry
    if isinstance(exc, ClientResponseError) and exc.status >= 500:
        return True
    return False


_retry = retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential_jitter(initial=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)


def _check_response(resp: aiohttp.ClientResponse, url: str) -> None:
    if resp.status == 429:
        raise RateLimitError(f"Rate limited: {url}")
    if resp.status >= 500:
        raise ClientResponseError(
            request_info=resp.request_info,
            history=resp.history,
            status=resp.status,
            message="Server error",
            headers=resp.headers,
        )
    if resp.status in (401, 403):
        raise Exception(f"Auth error {url}: status={resp.status}")
    if resp.status != 200:
        raise Exception(f"API error {url}: status={resp.status}")


class Fetcher:
    def fetch_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 15,
    ):
        pass


class GetFetcher(Fetcher):

    @_retry
    async def fetch_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 15,
    ) -> Json:
        async with session.get(
            url, params=params, headers=headers, timeout=ClientTimeout(timeout)
        ) as resp:
            _check_response(resp, url)
            return await resp.json()


class PostFetcher(Fetcher):

    @_retry
    async def fetch_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 15,
    ) -> Json | None:
        async with session.post(
            url, params=params, headers=headers, timeout=ClientTimeout(timeout)
        ) as resp:
            _check_response(resp, url)
            return await resp.json()
