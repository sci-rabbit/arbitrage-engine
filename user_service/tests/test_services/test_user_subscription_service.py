from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from services.user_subscription_service import UserSubscriptionService
from tests.factories import make_subscription, make_user, make_user_subscription


async def test_get_active_returns_sub(db: AsyncSession):
    user = await make_user(db, email="usub1@test.com")
    sub = await make_subscription(db, name="USub1")
    user_sub = await make_user_subscription(
        db, user_id=user.id, subscription_id=sub.id,
        expired_at=datetime.now(UTC) + timedelta(days=30),
    )
    result = await UserSubscriptionService(db).get_active(user.id, sub.id)
    assert result is not None
    assert result.id == user_sub.id


async def test_get_active_returns_none_when_expired(db: AsyncSession):
    user = await make_user(db, email="usub2@test.com")
    sub = await make_subscription(db, name="USub2")
    await make_user_subscription(
        db, user_id=user.id, subscription_id=sub.id,
        expired_at=datetime.now(UTC) - timedelta(days=1),
    )
    result = await UserSubscriptionService(db).get_active(user.id, sub.id)
    assert result is None


async def test_get_active_returns_none_when_not_found(db: AsyncSession):
    user = await make_user(db, email="usub3@test.com")
    sub = await make_subscription(db, name="USub3")
    result = await UserSubscriptionService(db).get_active(user.id, sub.id)
    assert result is None


async def test_list_active_returns_non_expired(db: AsyncSession):
    user = await make_user(db, email="usub4@test.com")
    sub1 = await make_subscription(db, name="USub4a")
    sub2 = await make_subscription(db, name="USub4b")
    active = await make_user_subscription(
        db, user_id=user.id, subscription_id=sub1.id,
        expired_at=datetime.now(UTC) + timedelta(days=10),
    )
    await make_user_subscription(
        db, user_id=user.id, subscription_id=sub2.id,
        expired_at=datetime.now(UTC) - timedelta(days=1),
    )
    result = await UserSubscriptionService(db).list_active(user.id)
    ids = {s.id for s in result}
    assert active.id in ids
    assert all(s.expired_at > datetime.now(UTC) for s in result)
