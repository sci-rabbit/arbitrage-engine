from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dto.subscription_dto import CreateSubDTO, UpdateSubDTO
from exceptions.subscription import SubscriptionAlreadyExists, SubscriptionNotFound
from services.subscription.admin_subscription_service import AdminSubscriptionService
from tests.factories import make_subscription


async def test_create_subscription(db: AsyncSession):
    sub = await AdminSubscriptionService(db).create_subscription(
        CreateSubDTO(subscription_name="Weekly", price=Decimal("9.99"), duration_days=7)
    )
    assert sub.id is not None
    assert sub.subscription_name == "Weekly"
    assert sub.price == Decimal("9.99")
    assert sub.duration_days == 7


async def test_create_raises_on_duplicate_name(db: AsyncSession):
    await make_subscription(db, name="Dup")
    with pytest.raises(SubscriptionAlreadyExists):
        await AdminSubscriptionService(db).create_subscription(
            CreateSubDTO(subscription_name="Dup", price=Decimal("9.99"), duration_days=7)
        )


async def test_get_by_id_found(db: AsyncSession):
    sub = await make_subscription(db, name="GetById")
    result = await AdminSubscriptionService(db).get_by_id(sub.id)
    assert result.id == sub.id


async def test_get_by_id_raises_not_found(db: AsyncSession):
    with pytest.raises(SubscriptionNotFound):
        await AdminSubscriptionService(db).get_by_id(999_999)


async def test_list_returns_subscriptions(db: AsyncSession):
    await make_subscription(db, name="PlanA")
    await make_subscription(db, name="PlanB")
    result = await AdminSubscriptionService(db).list(limit=100)
    names = {s.subscription_name for s in result}
    assert {"PlanA", "PlanB"}.issubset(names)


async def test_update_subscription_changes_name(db: AsyncSession):
    sub = await make_subscription(db, name="OldName")
    updated = await AdminSubscriptionService(db).update_subscription(
        sub, UpdateSubDTO(subscription_name="NewName")
    )
    assert updated.subscription_name == "NewName"


async def test_update_ignores_none_fields(db: AsyncSession):
    sub = await make_subscription(db, name="Stable", price=Decimal("9.99"))
    updated = await AdminSubscriptionService(db).update_subscription(
        sub, UpdateSubDTO(price=Decimal("19.99"))
    )
    assert updated.subscription_name == "Stable"
    assert updated.price == Decimal("19.99")


async def test_delete_subscription(db: AsyncSession):
    sub = await make_subscription(db, name="ToDelete")
    sub_id = sub.id
    await AdminSubscriptionService(db).delete_subscription(sub)
    await db.flush()
    with pytest.raises(SubscriptionNotFound):
        await AdminSubscriptionService(db).get_by_id(sub_id)
