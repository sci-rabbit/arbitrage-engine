from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dto.user_subscription_dto import ExtendSubscriptionDTO, GrantSubscriptionDTO
from exceptions.user_subscription import UserSubscriptionNotFound
from services.admin_user_subscription_service import AdminUserSubscriptionService
from tests.factories import make_subscription, make_user, make_user_subscription


def naive_utc(days: int = 0) -> datetime:
    """SQLite хранит naive datetimes — используем naive во всех тестах где значение уходит в DB."""
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(days=days)


async def test_grant_creates_new_subscription(db: AsyncSession):
    user = await make_user(db, email="ag1@test.com")
    sub = await make_subscription(db, name="AG1")

    result = await AdminUserSubscriptionService(db).grant(
        GrantSubscriptionDTO(user_id=user.id, subscription_id=sub.id, expired_at=naive_utc(30))
    )

    assert result.id is not None
    assert result.user_id == user.id
    assert result.subscription_id == sub.id
    assert result.is_active is True


async def test_grant_updates_existing_if_new_date_is_later(db: AsyncSession):
    user = await make_user(db, email="ag2@test.com")
    sub = await make_subscription(db, name="AG2")
    await make_user_subscription(db, user_id=user.id, subscription_id=sub.id, expired_at=naive_utc(10))

    new_date = naive_utc(60)
    result = await AdminUserSubscriptionService(db).grant(
        GrantSubscriptionDTO(user_id=user.id, subscription_id=sub.id, expired_at=new_date)
    )

    assert result.expired_at >= new_date


async def test_grant_keeps_existing_if_already_later(db: AsyncSession):
    user = await make_user(db, email="ag3@test.com")
    sub = await make_subscription(db, name="AG3")
    far_future = naive_utc(100)
    await make_user_subscription(db, user_id=user.id, subscription_id=sub.id, expired_at=far_future)

    result = await AdminUserSubscriptionService(db).grant(
        GrantSubscriptionDTO(user_id=user.id, subscription_id=sub.id, expired_at=naive_utc(5))
    )

    assert result.expired_at >= far_future


async def test_extend_adds_days(db: AsyncSession):
    user = await make_user(db, email="ag4@test.com")
    sub = await make_subscription(db, name="AG4")
    original = naive_utc(10)
    await make_user_subscription(db, user_id=user.id, subscription_id=sub.id, expired_at=original)

    # datetime.now(UTC) в сервисе вернёт aware — патчим чтобы вернуть naive (SQLite)
    with patch("services.admin_user_subscription_service.datetime") as mock_dt:
        mock_dt.now.return_value = datetime.now(UTC).replace(tzinfo=None)
        result = await AdminUserSubscriptionService(db).extend(
            user.id, sub.id, ExtendSubscriptionDTO(days=20)
        )

    assert result.expired_at > original


async def test_extend_raises_when_not_found(db: AsyncSession):
    user = await make_user(db, email="ag5@test.com")
    sub = await make_subscription(db, name="AG5")

    with pytest.raises(UserSubscriptionNotFound):
        await AdminUserSubscriptionService(db).extend(
            user.id, sub.id, ExtendSubscriptionDTO(days=10)
        )


async def test_revoke_sets_inactive(db: AsyncSession):
    user = await make_user(db, email="ag6@test.com")
    sub = await make_subscription(db, name="AG6")
    await make_user_subscription(db, user_id=user.id, subscription_id=sub.id)

    await AdminUserSubscriptionService(db).revoke(user.id, sub.id)

    from repositrories.user_subscription_repository import UserSubscriptionRepository
    record = await UserSubscriptionRepository(db).get_by_user_and_subscription(user.id, sub.id)
    assert record.is_active is False


async def test_list_all_by_user(db: AsyncSession):
    user = await make_user(db, email="ag7@test.com")
    sub1 = await make_subscription(db, name="AG7a")
    sub2 = await make_subscription(db, name="AG7b")
    us1 = await make_user_subscription(db, user_id=user.id, subscription_id=sub1.id)
    us2 = await make_user_subscription(db, user_id=user.id, subscription_id=sub2.id)

    result = await AdminUserSubscriptionService(db).list_all_by_user(user.id)
    ids = {s.id for s in result}
    assert {us1.id, us2.id}.issubset(ids)
