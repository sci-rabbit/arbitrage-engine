from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OrderbookOut(BaseModel):
    platform_market_id: str
    orderbook: dict[str, Any] | None = None
    updated_at: datetime

