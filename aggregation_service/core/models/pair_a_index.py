from common.models.base import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class PairAIndex(Base):
    __tablename__ = "pair_a_index"

    pair_id: Mapped[int] = mapped_column(
        ForeignKey("pairs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    a_market_id: Mapped[str]
    final_score: Mapped[float]
