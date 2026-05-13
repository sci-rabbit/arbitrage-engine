from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dto.subscription_dto import CreateSubDTO, UpdateSubDTO
from exceptions.subscription import SubscriptionAlreadyExists, SubscriptionNotFound
from models.subscription import Subscription
from repositrories.order_repository import OrderRepository
from repositrories.subsctiption_repository import SubscriptionRepository


class AdminSubscriptionService:
    def __init__(self, session: AsyncSession):
        self.subscription_repo = SubscriptionRepository(session)
        self.order_repo = OrderRepository(session)
        self.session = session

    async def _get_or_raise(self, **filters) -> Subscription:
        sub = await self.subscription_repo.get_one_by(**filters)
        if sub is None:
            raise SubscriptionNotFound()
        return sub

    async def create_subscription(self, sub_dto: CreateSubDTO) -> Subscription:
        try:
            sub = await self.subscription_repo.create(
                subscription_name=sub_dto.subscription_name,
                price=sub_dto.price,
                duration_days=sub_dto.duration_days,
            )
            return sub
        except IntegrityError:
            raise SubscriptionAlreadyExists()

    async def get_by_id(self, sub_id: int) -> Subscription | None:
        return await self._get_or_raise(id=sub_id)

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        **filters,
    ) -> List[Subscription]:
        return await self.subscription_repo.paginate(
            limit=limit,
            offset=offset,
            **filters,
        )

    async def update_subscription(
        self,
        sub: Subscription,
        sub_dto: UpdateSubDTO,
    ) -> Subscription:
        sub_data = {k: v for k, v in sub_dto.__dict__.items() if v is not None}
        return await self.subscription_repo.update(
            obj=sub,
            obj_data=sub_data,
        )

    async def delete_subscription(self, sub: Subscription) -> None:
        await self.subscription_repo.delete(sub)
