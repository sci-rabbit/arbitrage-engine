"""
Admin API tests.

Фокус: access control (403 для не-админов) + happy path для ключевых операций.
Бизнес-логику не перепроверяем — это покрыто service-тестами.
"""
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, make_admin, make_subscription, make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _admin_headers(db):
    admin = await make_admin(db, email="admin@test.com")
    return auth_headers(admin)


# ---------------------------------------------------------------------------
# Access control — проверяем что обычный юзер получает 403
# ---------------------------------------------------------------------------

async def test_list_users_requires_admin(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="noadmin@test.com")
    r = await client.get("/admin/users", headers=auth_headers(user))
    assert r.status_code == 403


async def test_list_users_requires_auth(client: AsyncClient):
    r = await client.get("/admin/users")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Admin users
# ---------------------------------------------------------------------------

async def test_admin_list_users_returns_200(client: AsyncClient, db: AsyncSession):
    await make_user(db, email="listed@test.com", username="listed")
    r = await client.get("/admin/users", headers=await _admin_headers(db))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_admin_get_user_returns_200(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="getuser@test.com", username="getuser")
    r = await client.get(f"/admin/users/{user.id}", headers=await _admin_headers(db))
    assert r.status_code == 200
    assert r.json()["id"] == user.id


async def test_admin_get_user_returns_404(client: AsyncClient, db: AsyncSession):
    r = await client.get("/admin/users/999999", headers=await _admin_headers(db))
    assert r.status_code == 404


async def test_admin_search_users(client: AsyncClient, db: AsyncSession):
    await make_user(db, email="searchable@test.com", username="searchable")
    r = await client.get("/admin/users/search?q=searchable", headers=await _admin_headers(db))
    assert r.status_code == 200
    assert any(u["email"] == "searchable@test.com" for u in r.json())


async def test_admin_grant_access(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="togrant@test.com", username="togrant", has_access=False)
    r = await client.post(f"/admin/users/{user.id}/grant-access", headers=await _admin_headers(db))
    assert r.status_code == 200
    assert r.json()["has_access"] is True


async def test_admin_revoke_access(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="torevoke@test.com", username="torevoke", has_access=True)
    r = await client.post(f"/admin/users/{user.id}/revoke-access", headers=await _admin_headers(db))
    assert r.status_code == 200
    assert r.json()["has_access"] is False


async def test_admin_delete_user_returns_204(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="todelete@test.com", username="todelete")
    r = await client.delete(f"/admin/users/{user.id}", headers=await _admin_headers(db))
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Admin subscriptions
# ---------------------------------------------------------------------------

async def test_admin_create_subscription_returns_201(client: AsyncClient, db: AsyncSession):
    r = await client.post(
        "/admin/subscriptions",
        headers=await _admin_headers(db),
        json={"subscription_name": "Pro", "price": "29.99", "duration_days": 30},
    )
    assert r.status_code == 201
    assert r.json()["subscription_name"] == "Pro"


async def test_admin_create_subscription_requires_admin(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="nosub@test.com", username="nosub")
    r = await client.post(
        "/admin/subscriptions",
        headers=auth_headers(user),
        json={"subscription_name": "X", "price": "9.99", "duration_days": 7},
    )
    assert r.status_code == 403


async def test_admin_delete_subscription_returns_204(client: AsyncClient, db: AsyncSession):
    sub = await make_subscription(db, name="ToDeleteSub")
    r = await client.delete(f"/admin/subscriptions/{sub.id}", headers=await _admin_headers(db))
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Admin transactions
# ---------------------------------------------------------------------------

async def test_admin_deposit_returns_201(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="admindep@test.com", username="admindep")
    r = await client.post(
        f"/admin/users/{user.id}/transactions/deposit",
        headers=await _admin_headers(db),
        json={"amount": "100.00"},
    )
    assert r.status_code == 201
    assert Decimal(r.json()["amount"]) == Decimal("100.00")


async def test_admin_list_all_transactions(client: AsyncClient, db: AsyncSession):
    r = await client.get("/admin/transactions", headers=await _admin_headers(db))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_admin_list_transactions_filter_by_type(client: AsyncClient, db: AsyncSession):
    r = await client.get("/admin/transactions?type=deposit", headers=await _admin_headers(db))
    assert r.status_code == 200


async def test_admin_list_transactions_invalid_type(client: AsyncClient, db: AsyncSession):
    r = await client.get("/admin/transactions?type=invalid", headers=await _admin_headers(db))
    assert r.status_code == 422
