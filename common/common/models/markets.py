from typing import Optional, Any

import numpy as np
from pgvector.sqlalchemy import VECTOR
from sqlalchemy import String, Boolean, Numeric, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base, IDMixin


def _parse_emb(value) -> Optional[np.ndarray]:
    if value is None:
        return None
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, str):
        import ast
        return np.array(ast.literal_eval(value), dtype=np.float32)
    return np.array(value, dtype=np.float32)


class Market(IDMixin, Base):
    __tablename__ = "markets"

    platform: Mapped[str] = mapped_column(String, nullable=False, index=True)
    platform_market_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    event_id: Mapped[str] = mapped_column(String, index=True)
    event_slug: Mapped[str] = mapped_column(String, index=True, nullable=True)
    series_ticker: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    category: Mapped[str] = mapped_column(String)

    title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    outcomes: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=True)
    token_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)

    liquidity: Mapped[Optional[float]] = mapped_column(Numeric)
    volume_24h: Mapped[Optional[float]] = mapped_column(Numeric)

    open_time: Mapped[Optional[Any]] = mapped_column(TIMESTAMP(timezone=True))
    close_time: Mapped[Optional[Any]] = mapped_column(TIMESTAMP(timezone=True))

    semantic_text: Mapped[Optional[str]] = mapped_column(Text)
    embedding: Mapped[Optional[list]] = mapped_column(VECTOR(768))
    semantic_embedding: Mapped[Optional[list]] = mapped_column(VECTOR(768))

    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)

    def __repr__(self) -> str:
        return f"<Market platform={self.platform} id={self.platform_market_id}>"


def market_from_row(prefix: str, row) -> "Market":
    m = Market(
        id=row[f"{prefix}_id"],
        platform=row[f"{prefix}_platform"],
        platform_market_id=row[f"{prefix}_market_id"],
        title=row[f"{prefix}_title"],
        normalized_title=row.get(f"{prefix}_normalized_title"),
        semantic_text=row.get(f"{prefix}_semantic_text"),
        description=row.get(f"{prefix}_description"),
        embedding=row[f"{prefix}_embedding"],
        semantic_embedding=row[f"{prefix}_semantic_embedding"],
        close_time=row.get(f"{prefix}_close_time"),
        outcomes=row.get(f"{prefix}_outcomes"),
    )
    m._embedding_np = _parse_emb(m.embedding)
    m._semantic_embedding_np = _parse_emb(m.semantic_embedding)
    return m