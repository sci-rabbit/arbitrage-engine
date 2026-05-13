
from pydantic import BaseModel

from core.schemas.markets import MarketShort


class ArbitrageOpportunity(BaseModel):
    direction: str

    # Входные цены
    entry_price_1: float
    entry_price_2: float
    entry_spread: float
    min_size_per_market: float

    # Минимальный и максимальный spread по стакану
    min_spread: float
    avg_sum_at_min_spread: float
    pnl_at_min_spread: float

    max_spread: float
    avg_sum_at_max_spread: float
    pnl_at_max_spread: float

    # Итоговые показатели по реально выкупленным контрактам
    final_contracts: float
    final_cost: float
    final_avg_price: float
    final_spread: float
    final_pnl: float


class ArbitrageResult(BaseModel):
    distance: float
    final_score: float
    market_a: MarketShort
    market_b: MarketShort
    arbitrage: list[ArbitrageOpportunity]
