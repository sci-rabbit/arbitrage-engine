
from sqlalchemy import select

from core import Market
from core.repositories.market_repository import MarketRepository


class KalshiRepository(MarketRepository):

    async def search(self, common_id: str) -> list[Market]:
        query = (
            select(Market)
            .where(Market.event_id == common_id)
            .where(Market.platform == "kalshi")
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
