
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.order import OrderNotFound
from models.order import Order
from repositrories.order_repository import OrderRepository


class OrderService:
    def __init__(self, session: AsyncSession):
        self.order_repo = OrderRepository(session)

    async def _get_or_raise(self, **filters) -> Order:
        order = await self.order_repo.get_one_by(**filters)
        if order is None:
            raise OrderNotFound()
        return order

    async def get_by_id(self, order_id: int) -> Order:
        return await self._get_or_raise(id=order_id)

    async def list_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        return await self.order_repo.paginate(
            limit=limit,
            offset=offset,
            user_id=user_id,
        )

    async def delete(self, order: Order) -> None:
        await self.order_repo.delete(obj=order)
