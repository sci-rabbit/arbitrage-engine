import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.order import OrderNotFound
from services.order_service import OrderService
from tests.factories import make_order, make_user


async def test_get_by_id_found(db: AsyncSession):
    user = await make_user(db, email="ord1@test.com")
    order = await make_order(db, user_id=user.id)
    result = await OrderService(db).get_by_id(order.id)
    assert result.id == order.id


async def test_get_by_id_raises_not_found(db: AsyncSession):
    with pytest.raises(OrderNotFound):
        await OrderService(db).get_by_id(999_999)


async def test_list_by_user_returns_orders(db: AsyncSession):
    user = await make_user(db, email="ord2@test.com")
    o1 = await make_order(db, user_id=user.id)
    o2 = await make_order(db, user_id=user.id)
    orders = await OrderService(db).list_by_user(user.id)
    ids = {o.id for o in orders}
    assert {o1.id, o2.id}.issubset(ids)


async def test_list_by_user_excludes_other_users(db: AsyncSession):
    u1 = await make_user(db, email="ord3a@test.com", username="ord3a")
    u2 = await make_user(db, email="ord3b@test.com", username="ord3b")
    await make_order(db, user_id=u1.id)
    o2 = await make_order(db, user_id=u2.id)
    orders = await OrderService(db).list_by_user(u1.id)
    assert all(o.id != o2.id for o in orders)


async def test_delete_order(db: AsyncSession):
    user = await make_user(db, email="ord4@test.com")
    order = await make_order(db, user_id=user.id)
    order_id = order.id
    await OrderService(db).delete(order)
    await db.flush()
    with pytest.raises(OrderNotFound):
        await OrderService(db).get_by_id(order_id)
