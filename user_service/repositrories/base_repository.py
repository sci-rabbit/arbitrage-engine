import builtins
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

Model = TypeVar("Model")


class AsyncRepository(Generic[Model]):
    model: type[Model] = None

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, obj_id: int) -> Model | None:
        return await self.session.get(self.model, obj_id)

    async def get_one_by(self, **filters) -> Model | None:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def paginate(
        self,
        limit: int = 10,
        offset: int = 0,
        **filters,
    ):
        stmt = select(self.model)

        if filters:
            stmt = stmt.filter_by(**filters)

        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Model]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by(
        self,
        limit: int = 50,
        offset: int = 0,
        **filters,
    ) -> builtins.list[Model]:
        stmt = select(self.model).filter_by(**filters).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> Model:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(
        self,
        obj: Model,
        obj_data: dict[str, Any],
    ) -> Model:
        obj = await self.session.merge(obj)
        for name, value in obj_data.items():
            setattr(obj, name, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: Model) -> None:
        obj = await self.session.merge(obj)
        await self.session.delete(obj)
