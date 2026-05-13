from sqlalchemy import ARRAY, TEXT, cast, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Pair
from core.repositories.base_repository import AsyncRepository


class PairRepository(AsyncRepository[Pair]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Pair)
        self.session = session

    async def delete_by_platform_market_id(self, platform_market_id: str) -> None:
        await self.session.execute(
            delete(Pair).where(
                Pair.market_ids.contains(platform_market_id),
            )
        )

    async def delete_many(self, platform_market_ids: list) -> None:
        await self.session.execute(
            delete(Pair).where(
                Pair.market_ids.op("?|")(cast(platform_market_ids, ARRAY(TEXT)))
            )
        )
