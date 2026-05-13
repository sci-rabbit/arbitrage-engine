from sqlalchemy.ext.asyncio import AsyncSession

from core.models.invalid_pairs import InvalidPair
from core.repositories.base_repository import AsyncRepository


class InvalidPairRepository(AsyncRepository[InvalidPair]):
    model = InvalidPair

    def __init__(self, session: AsyncSession):
        super().__init__(session)
