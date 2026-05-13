from datetime import datetime
from typing import List

from sqlalchemy import select

from models.user_subscriptions import UserSubscription
from repositrories.base_repository import AsyncRepository


class UserSubscriptionRepository(AsyncRepository[UserSubscription]):
    model = UserSubscription

    async def get_active(
        self,
        user_id: int,
        subscription_id: int,
        now: datetime,
    ) -> UserSubscription | None:
        stmt = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.expired_at > now,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_subscription(
        self,
        user_id: int,
        subscription_id: int,
    ) -> UserSubscription | None:
        stmt = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(
        self,
        user_id: int,
        now: datetime,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserSubscription]:
        stmt = (
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.expired_at > now,
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserSubscription]:
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
