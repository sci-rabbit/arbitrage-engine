from typing import TypeVar

from common.repositories.base_repository import AsyncRepository as _CommonRepository
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.base import Base

Model = TypeVar("Model", bound=Base)


class AsyncRepository(_CommonRepository[Model]):
    def __init__(self, session: AsyncSession, model: type[Model] = None):
        super().__init__(session)
        if model is not None:
            self.model = model
