from typing import Optional

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base, IDMixin


class Pair(IDMixin, Base):
    __tablename__ = "pairs"

    market_ids: Mapped[Optional[list]] = mapped_column(JSONB, unique=True)
    distance: Mapped[Optional[float]] = mapped_column(nullable=True)
    title_channel_score: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    semantic_channel_score: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(nullable=True)