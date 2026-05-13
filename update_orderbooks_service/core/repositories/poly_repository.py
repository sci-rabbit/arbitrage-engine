import json
from typing import Dict, Any, List

from sqlalchemy import select, and_, func, text

from core.models.markets import Market
from core.repositories.market_repository import (
    MarketRepository,
)
from sqlalchemy.orm import Session

from core.models.market_pairs import Pair


market_platform = "polymarket"

get_active_tickers_in_pa_query = text(
    """
            SELECT DISTINCT m.platform_market_id, m.token_ids
            FROM markets m
            WHERE m.platform = 'polymarket'
              AND m.close_time > now()
              AND EXISTS (
                SELECT 1
                FROM pairs p,
                     jsonb_array_elements_text(p.market_ids) mid
                WHERE mid = m.platform_market_id
            )
            """
)


class PolymarketRepository(MarketRepository):

    async def get_active_markets(self) -> List[Market]:
        query = select(Market).where(
            and_(Market.platform == market_platform, Market.close_time > func.now())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_markets_in_pairs(self) -> List[Market]:
        query = select(Market).where(
            and_(
                Market.platform == market_platform,
                Market.close_time > func.now(),
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
        return [
            {
                "platform_market_id": row[0],
                "token_ids": row[1],
            }
            for row in result.fetchall()
            if row[0]
        ]

    async def get_market_by_token_ids(self, token_ids) -> Market | None:
        query = select(Market).where(Market.token_ids == token_ids)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_token_ids_and_market_id(
        self,
    ) -> Dict[str, Any]:
        rows = await self.get_active_markets_in_pairs()

        mapping = {}

        for market in rows:
            market_id, token_ids = market.platform_market_id, market.token_ids
            token_ids = json.loads(token_ids)
            if not token_ids or len(token_ids) != 2:
                continue
            yes, no = token_ids
            mapping[yes] = (market_id, "yes")
            mapping[no] = (market_id, "no")

        return mapping


class PolymarketSyncRepository:
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
