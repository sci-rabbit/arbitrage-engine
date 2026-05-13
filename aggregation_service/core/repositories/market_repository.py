import logging

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import Market
from core.repositories.base_repository import AsyncRepository
from core.repositories.queries import query_for_cleanup_top_n, query_for_find_pairs

logger = logging.getLogger(__name__)


class MarketRepository(AsyncRepository[Market]):
    model = Market

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_platforms(self) -> list[str]:
        query = select(distinct(Market.platform))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_platform_market_id(self, platform_market_id: str) -> Market | None:
        query = select(Market).where(Market.platform_market_id == platform_market_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def search_by_query(
        self,
        text: str,
        platform: str,
    ) -> list[Market]:
        query = (
            select(Market)
            .where(Market.normalized_title == text)
            .where(Market.platform == platform)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def find_pairs(
        self,
        limit: int,
        offset: int,
        max_distance: float,
        pair_limit: int = 20,
    ):
        sql = query_for_find_pairs

        logger.info("Send request to db")
        rows = (
            (
                await self.session.execute(
                    sql,
                    {
                        "limit": limit,
                        "offset": offset,
                        "max_distance": max_distance,
                        "pair_limit": pair_limit,
                    },
                )
            )
            .mappings()
            .all()
        )
        logger.info("Got response rows=%s", len(rows))
        return rows

    async def cleanup_top_n(self, top_n: int) -> int:
        """
        Удаляет пары, которые не входят в top-N по final_score
        для каждого a_market_id.

        Возвращает количество удалённых пар.
        """
        stmt = query_for_cleanup_top_n

        result = await self.session.execute(stmt, {"top_n": top_n})
        await self.session.commit()

        deleted = result.rowcount  # type: ignore[attr-defined]
        return deleted or 0
