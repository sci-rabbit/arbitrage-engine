from datetime import datetime
from typing import List

from pydantic import BaseModel


class DeleteMarketsBody(BaseModel):
    market_ids: List[str]


class MarketShort(BaseModel):
    platform: str
    platform_market_id: str
    title: str
    description: str | None = None
    close_time: datetime | None = None
    url: str | None = None


class MarketPair(BaseModel):
    market_a: MarketShort
    market_b: MarketShort
    final_score: float
    distance: float
    channels: dict
