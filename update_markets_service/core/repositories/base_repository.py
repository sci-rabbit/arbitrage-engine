from typing import TypeVar, Type

from sqlalchemy.ext.asyncio import AsyncSession

from common.repositories.base_repository import AsyncRepository as _CommonRepository
from core.models.base import Base

Model = TypeVar("Model", bound=Base)


class AsyncRepository(_CommonRepository[Model]):
    def __init__(self, session: AsyncSession, model: Type[Model] = None):
        super().__init__(session)
        if model is not None:
            self.model = model