from typing import List, Any, Dict

from sqlalchemy import select, and_, func, text
from sqlalchemy.orm import Session

from core import Market
from core.models.market_pairs import Pair
from core.repositories.market_repository import MarketRepository


market_platform = "predict_fun"

get_active_tickers_in_pa_query = text(
    """
            SELECT DISTINCT m.platform_market_id, m.token_ids
            FROM markets m
            WHERE m.platform = 'predict_fun'
              AND EXISTS (
                SELECT 1
                FROM pairs p,
                     jsonb_array_elements_text(p.market_ids) mid
                WHERE mid = m.platform_market_id
            )
            """
)


class PredictfunRepository(MarketRepository):

    async def get_active_markets(self) -> List[Market]:
        query = select(Market).where(Market.platform == market_platform)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_markets_in_pairs(self) -> List[Market]:
        query = select(Market).where(
            and_(
                Market.platform == market_platform,
                Market.platform_market_id.in_(
                    select(func.jsonb_array_elements_text(Pair.market_ids))
                ),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_tickers_in_pairs(self) -> List[Dict[str, Any]]:
        query = get_active_tickers_in_pa_query
        result = await self.session.execute(query)
        return [row[0] for row in result.fetchall() if row[0]]


class PredictfunSyncRepository:
    def __init__(self, session: Session):
        self.session = session

    def update_orderbook(
        self, platform_market_id: str, orderbook: Dict[str, Any]
    ) -> Market | None:
        market = (
            self.session.query(Market)
            .filter(Market.platform_market_id == platform_market_id)
            .first()
        )
        if not market:
            return None
        market.orderbook = orderbook
        self.session.flush()
        return market
