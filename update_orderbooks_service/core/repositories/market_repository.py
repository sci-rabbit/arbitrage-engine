from sqlalchemy import select

from core.models.markets import Market
from core.repositories.base_repository import AsyncRepository


class MarketRepository(AsyncRepository[Market]):

    async def get_by_platform_market_id(self, platform_market_id: str) -> Market | None:
        query = select(Market).where(Market.platform_market_id == platform_market_id)
        result = await self.session.execute(query)
        return result.scalars().first()
