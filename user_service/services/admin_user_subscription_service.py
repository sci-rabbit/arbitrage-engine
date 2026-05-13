from datetime import datetime, timedelta, UTC
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from dto.user_subscription_dto import GrantSubscriptionDTO, ExtendSubscriptionDTO
from exceptions.user_subscription import UserSubscriptionNotFound
from models.user_subscriptions import UserSubscription
from repositrories.user_subscription_repository import UserSubscriptionRepository
from services.user_subscription_service import UserSubscriptionService


class AdminUserSubscriptionService(UserSubscriptionService):
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.session = session

    async def _get_or_raise(
        self,
        user_id: int,
        subscription_id: int,
    ) -> UserSubscription:
        sub = await self.user_sub_repo.get_by_user_and_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
        )
        if sub is None:
            raise UserSubscriptionNotFound()
        return sub

    async def list_all_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserSubscription]:
        return await self.user_sub_repo.get_all_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def grant(self, dto: GrantSubscriptionDTO) -> UserSubscription:
        existing = await self.user_sub_repo.get_by_user_and_subscription(
            user_id=dto.user_id,
            subscription_id=dto.subscription_id,
        )

        if existing:
            existing.expired_at = max(existing.expired_at, dto.expired_at)
            existing.is_active = True
            await self.session.flush()
            return existing

        sub = UserSubscription(
            user_id=dto.user_id,
            subscription_id=dto.subscription_id,
            started_at=datetime.now(UTC),
            expired_at=dto.expired_at,
            is_active=True,
        )
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def extend(
        self,
        user_id: int,
        subscription_id: int,
        dto: ExtendSubscriptionDTO,
    ) -> UserSubscription:
        sub = await self._get_or_raise(user_id, subscription_id)

        now = datetime.now(UTC)
        base = max(sub.expired_at, now)
        sub.expired_at = base + timedelta(days=dto.days)

        await self.session.flush()
        return sub

    async def revoke(self, user_id: int, subscription_id: int) -> None:
        sub = await self._get_or_raise(user_id, subscription_id)
        sub.is_active = False
        sub.expired_at = datetime.now(UTC)
        await self.session.flush()
