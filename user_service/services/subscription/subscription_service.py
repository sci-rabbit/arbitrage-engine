from datetime import datetime, timedelta, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.transaction import NotEnoughBalance
from models.subscription import Subscription
from models.user_subscriptions import UserSubscription
from models.order import Order
from repositrories.order_repository import OrderRepository
from repositrories.user_repository import UserRepository
from repositrories.user_subscription_repository import UserSubscriptionRepository
from repositrories.user_transaction_repository import UserTransactionRepository


class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.order_repo = OrderRepository(session)
        self.user_repo = UserRepository(session)
        self.user_sub_repo = UserSubscriptionRepository(session)
        self.transaction_repo = UserTransactionRepository(session)
        self.session = session

    async def buy_subscription(
        self,
        user_id: int,
        subscription: Subscription,
        count: int,
    ) -> Order:
        user = await self.user_repo.get_for_update(user_id)

        total_price = subscription.price * count

        if user.balance < total_price:
            raise NotEnoughBalance()

        user.balance -= total_price

        order = await self.order_repo.create_order(
            subscription=subscription,
            count=count,
            user_id=user.id,
        )

        await self.transaction_repo.create_transaction(
            user_id=user.id,
            amount=-total_price,
            type="purchase",
            description=f"Buy subscription {subscription.id}",
        )

        now = datetime.now(UTC)
        duration = timedelta(days=subscription.duration_days * count)
        expired_at = now + duration

        active_sub = await self.user_sub_repo.get_active(
            user_id=user.id,
            subscription_id=subscription.id,
            now=now,
        )

        if active_sub:
            active_sub.expired_at += duration
        else:
            new_sub = UserSubscription(
                user_id=user.id,
                subscription_id=subscription.id,
                started_at=now,
                expired_at=expired_at,
            )
            self.session.add(new_sub)

        user.subs_count += count
        user.orders_count += 1

        await self.session.flush()

        return order
