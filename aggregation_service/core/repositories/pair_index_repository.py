from sqlalchemy.ext.asyncio import AsyncSession

from core.models.pair_a_index import PairAIndex
from core.repositories.base_repository import AsyncRepository


class PairAIndexRepository(AsyncRepository[PairAIndex]):
    model = PairAIndex

    def __init__(self, session: AsyncSession):
        super().__init__(session)
