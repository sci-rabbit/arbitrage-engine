from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class OrderbookOut(BaseModel):
    platform_market_id: str
    orderbook: Optional[Dict[str, Any]] = None
    updated_at: datetime

