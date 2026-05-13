from typing import Dict, Any, List

from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import Session

from core.models.markets import Market
from core.repositories.market_repository import (
    MarketRepository,
)


market_platform = "kalshi"

get_active_tickers_in_pa_query = text(
            """
            SELECT DISTINCT m.platform_market_id
            FROM markets m
            WHERE m.platform = 'kalshi'
              AND m.close_time > now()
              AND EXISTS (
                SELECT 1
                FROM pairs p,
                     jsonb_array_elements_text(p.market_ids) mid
                WHERE mid = m.platform_market_id
            )
            """
        )


class KalshiRepository(MarketRepository):

    async def get_active_markets(self) -> List[Market]:
        query = select(Market).where(
            and_(Market.platform == market_platform, Market.close_time > func.now())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_tickers(self) -> List[str]:
        markets = await self.get_active_markets()
        return [
            market.platform_market_id for market in markets if market.platform_market_id
        ]


    async def get_active_tickers_in_pairs(self) -> List[str]:
        query = get_active_tickers_in_pa_query

        result = await self.session.execute(query)
        return [row[0] for row in result.fetchall() if row[0]]


class KalshiSyncRepository:
    def __init__(self, session: Session):
        self.session = session

    def update_orderbook(
        self, platform_market_id: str, orderbook: Dict[str, Any]
    ) -> Market | None:
        market = (
            self.session.query(Market)
            .filter(
                and_(
                    Market.platform == market_platform,
                    Market.platform_market_id == platform_market_id,
                )
            )
            .first()
        )
        if not market:
            return None
        market.orderbook = orderbook
        self.session.flush()
        return market
