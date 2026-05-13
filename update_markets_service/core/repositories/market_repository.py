
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Market
from core.repositories.base_repository import AsyncRepository


class MarketRepository(AsyncRepository[Market]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Market)
        self.session = session

    async def get_existing_ids(self, platform: str) -> set[str]:
        query = select(Market.platform_market_id).where(Market.platform == platform)
        result = await self.session.execute(query)
        existing_ids = set(result.scalars().all())
        return existing_ids

    async def get_map_by_ids(
        self, platform: str, market_ids: list[str]
    ) -> dict[str, Market]:
        if not market_ids:
            return {}

        query = (
            select(Market)
            .where(Market.platform == platform)
            .where(Market.platform_market_id.in_(market_ids))
        )
        result = await self.session.execute(query)
        markets = result.scalars().all()

        return {str(m.platform_market_id): m for m in markets}

    async def get_by_platform_market_id(self, platform_market_id: str) -> Market | None:
        query = select(Market).where(Market.platform_market_id == platform_market_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_with_none_emb(self) -> list[Market]:
        query = select(Market).where(
            or_(
                Market.embedding.is_(None),
                Market.semantic_embedding.is_(None),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_many(self, platform_market_ids: list[str]) -> None:
        await self.session.execute(
            delete(Market).where(
                Market.platform_market_id.in_(platform_market_ids),
            )
        )
