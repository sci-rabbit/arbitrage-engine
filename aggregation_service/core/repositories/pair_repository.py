
from fastapi import HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST

from core import Market
from core.models.market_pairs import Pair
from core.repositories.base_repository import AsyncRepository


class PairRepository(AsyncRepository[Pair]):
    model = Pair

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add_pair(self, markets_ids_list: list[list]) -> list[Pair]:
        try:
            normalized_lists = [
                sorted(set(markets_ids)) for markets_ids in markets_ids_list
            ]

            pairs = [Pair(market_ids=ids) for ids in normalized_lists]

            self.session.add_all(pairs)
            await self.session.flush()

            return pairs

        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Pair already exists!",
            )

    async def delete_pair(self, market_ids: list) -> None:
        await self.session.execute(
            delete(Pair).where(
                and_(
                    Pair.market_ids.contains(market_ids),
                    Pair.market_ids.contained_by(market_ids),
                )
            )
        )

    async def get_all_market_ids(self) -> list[list[str]]:
        query = select(Pair.market_ids)
        result = await self.session.execute(query)
        market_ids_list = result.scalars().all()
        return [ids for ids in market_ids_list if ids]

    async def get_all_pairs_with_markets(
        self,
        threshold_distance: float = 0.7,
        threshold_final_score: float = 0.7,
        limit: int = 500,
        offset: int = 0,
    ) -> list[tuple[Pair, list[Market]]]:
        query_pairs = (
            select(Pair)
            .where(Pair.distance <= threshold_distance)
            .where(Pair.final_score >= threshold_final_score)
        ).limit(limit).offset(offset)
        result = await self.session.execute(query_pairs)
        pairs = result.scalars().all()

        if not pairs:
            return []

        market_ids_set = {
            mid for pair in pairs for mid in pair.market_ids if pair.market_ids
        }

        query_markets = select(Market).where(
            Market.platform_market_id.in_(market_ids_set)
        )
        result_markets = await self.session.execute(query_markets)
        markets = result_markets.scalars().all()

        markets_dict: dict[str, Market] = {m.platform_market_id: m for m in markets}

        pairs_with_markets: list[tuple[Pair, list[Market]]] = []
        for pair in pairs:
            pair_markets = [
                markets_dict[mid] for mid in pair.market_ids if mid in markets_dict
            ]
            pairs_with_markets.append((pair, pair_markets))

        return pairs_with_markets
