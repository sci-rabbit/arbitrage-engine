
import aiohttp
import structlog
from aiohttp import WSMsgType

from core.config import settings

logger = structlog.getLogger(__name__)


class EmbeddingClient:
    def __init__(
        self,
        texts: list[str] | str,
        aio_session: aiohttp.ClientSession,
    ):
        self.max_concurrent_requests = settings.embedding.max_concurrency
        self.url = settings.embedding.url
        self.ws_url = settings.embedding.ws_url
        self.texts = texts
        self.aio_session = aio_session
        self.params = {"text": self.texts}

    async def _fetch_ws(self, text):
        # POST /encode
        async with self.aio_session.post(
            settings.embedding.url, json={"texts": text}
        ) as resp:
            data = await resp.json()
            task_id = data["task_id"]

        async with self.aio_session.ws_connect(self.ws_url + task_id) as ws:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    return msg.json()

                if msg.type == WSMsgType.ERROR:
                    raise RuntimeError(f"WS error: {ws.exception()}")

                if msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSE):
                    break

        raise RuntimeError("WebSocket closed before TEXT message")

    async def get_embeddings(self) -> list[list[float]] | None:
        try:
            result = await self._fetch_ws(self.texts)

            if result.get("status") == "done":
                return result.get("embeddings")

        except Exception as e:
            logger.exception(
                "Error getting embeddings",
                e=str(e),
                exc_info=True,
            )
