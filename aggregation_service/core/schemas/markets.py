from datetime import datetime

from pydantic import BaseModel


class DeleteMarketsBody(BaseModel):
    market_ids: list[str]


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
