"""Tests for EmbeddingClient.get_embeddings."""
from unittest.mock import AsyncMock, patch

import pytest

from core.markets_embedding.embedding_client import EmbeddingClient


def _make_client(texts=None):
    session = AsyncMock()
    return EmbeddingClient(texts=texts or ["hello world"], aio_session=session)


@pytest.mark.asyncio
async def test_get_embeddings_returns_embeddings_on_done():
    client = _make_client()
    embeddings = [[0.1, 0.2, 0.3]]
    with patch.object(client, "_fetch_ws", new=AsyncMock(return_value={"status": "done", "embeddings": embeddings})):
        result = await client.get_embeddings()
    assert result == embeddings


@pytest.mark.asyncio
async def test_get_embeddings_status_not_done_returns_none():
    client = _make_client()
    with patch.object(client, "_fetch_ws", new=AsyncMock(return_value={"status": "pending"})):
        result = await client.get_embeddings()
    assert result is None


@pytest.mark.asyncio
async def test_get_embeddings_missing_status_returns_none():
    client = _make_client()
    with patch.object(client, "_fetch_ws", new=AsyncMock(return_value={"embeddings": [[0.1]]})):
        result = await client.get_embeddings()
    assert result is None


@pytest.mark.asyncio
async def test_get_embeddings_exception_returns_none():
    client = _make_client()
    with patch.object(client, "_fetch_ws", new=AsyncMock(side_effect=RuntimeError("WS error"))):
        result = await client.get_embeddings()
    assert result is None


@pytest.mark.asyncio
async def test_get_embeddings_passes_texts_to_fetch_ws():
    client = _make_client(texts=["question one", "question two"])
    mock_fetch = AsyncMock(return_value={"status": "done", "embeddings": [[0.1], [0.2]]})
    with patch.object(client, "_fetch_ws", new=mock_fetch):
        await client.get_embeddings()
    mock_fetch.assert_called_once_with(["question one", "question two"])
