from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, make_subscription, make_user


async def test_list_subscriptions_returns_200(client: AsyncClient, db: AsyncSession):
    await make_subscription(db, name="Weekly")
    r = await client.get("/subscriptions")
    assert r.status_code == 200
    names = [s["subscription_name"] for s in r.json()]
    assert "Weekly" in names


async def test_list_subscriptions_does_not_require_auth(client: AsyncClient):
    r = await client.get("/subscriptions")
    assert r.status_code == 200


async def test_my_subscriptions_returns_200(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="mysub@test.com")
    r = await client.get("/subscriptions/my", headers=auth_headers(user))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_my_subscriptions_returns_401_without_auth(client: AsyncClient):
    r = await client.get("/subscriptions/my")
    assert r.status_code == 401


async def test_my_orders_returns_200(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="myord@test.com")
    r = await client.get("/subscriptions/my/orders", headers=auth_headers(user))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_buy_subscription_returns_404_on_unknown_sub(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="buy404@test.com")
    r = await client.post("/subscriptions/999999/buy", headers=auth_headers(user))
    assert r.status_code == 404


async def test_buy_subscription_returns_401_without_auth(client: AsyncClient):
    r = await client.post("/subscriptions/1/buy")
    assert r.status_code == 401