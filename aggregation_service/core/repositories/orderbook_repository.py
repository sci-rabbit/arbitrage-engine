from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import Orderbook
from core.repositories.base_repository import AsyncRepository


class OrderbookRepository(AsyncRepository[Orderbook]):
    model = Orderbook

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_platform_market_ids(
        self, platform_market_ids: List[str]
    ) -> List[Orderbook]:
        query = select(Orderbook).where(
            Orderbook.platform_market_id.in_(platform_market_ids)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())