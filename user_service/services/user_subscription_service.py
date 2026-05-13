from datetime import datetime, UTC
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from models.user_subscriptions import UserSubscription
from repositrories.user_subscription_repository import UserSubscriptionRepository


class UserSubscriptionService:
    def __init__(self, session: AsyncSession):
        self.user_sub_repo = UserSubscriptionRepository(session)

    async def get_active(
        self,
        user_id: int,
        subscription_id: int,
    ) -> UserSubscription | None:
        now = datetime.now(UTC)
        return await self.user_sub_repo.get_active(
            user_id=user_id,
            subscription_id=subscription_id,
            now=now,
        )

    async def list_active(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserSubscription]:
        now = datetime.now(UTC)
        return await self.user_sub_repo.get_all_active(
            user_id=user_id,
            now=now,
            limit=limit,
            offset=offset,
        )
