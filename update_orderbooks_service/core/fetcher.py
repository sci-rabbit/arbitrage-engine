import asyncio
from typing import Any

import aiohttp
from aiohttp import ClientResponseError, ClientTimeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

Json = dict[str, Any] | list[dict[str, Any]] | list[Any]


RETRY_EXCEPTIONS = (
    aiohttp.ClientConnectorError,
    aiohttp.ServerTimeoutError,
    asyncio.TimeoutError,
)


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

    @retry(
        retry=retry_if_exception_type(RETRY_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.5, max=10),
        reraise=True,
    )
    async def fetch_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 15,
    ):
        async with session.get(
            url, params=params, headers=headers, timeout=ClientTimeout(timeout)
        ) as resp:
            if resp.status >= 500:
                raise ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message="Server error",
                    headers=resp.headers,
                )

            if resp.status != 200:
                raise Exception(f"API error {url}: status={resp.status}")
            return await resp.json()


class PostFetcher(Fetcher):

    @retry(
        retry=retry_if_exception_type(RETRY_EXCEPTIONS),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.5, max=10),
        reraise=True,
    )
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
            if resp.status >= 500:
                raise ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message="Server error",
                    headers=resp.headers,
                )

            if resp.status != 200:
                raise Exception(f"API error {url}: status={resp.status}")
            return await resp.json()
