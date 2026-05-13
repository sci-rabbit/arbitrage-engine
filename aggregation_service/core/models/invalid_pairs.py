from common.models.base import Base, IDMixin
from sqlalchemy import Index
from sqlalchemy.orm import Mapped


class InvalidPair(IDMixin, Base):
    __tablename__ = "invalid_pair"
    __table_args__ = (
        Index("ix_invalid_pair_ab", "a_market_id", "b_market_id"),
        Index("ix_invalid_pair_ba", "b_market_id", "a_market_id"),
    )

    a_market_id: Mapped[str]
    b_market_id: Mapped[str]
