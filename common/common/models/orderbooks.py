from typing import Optional, Dict, Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import Base, IDMixin


class Orderbook(IDMixin, Base):
    __tablename__ = "orderbooks"

    platform_market_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    orderbook: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)