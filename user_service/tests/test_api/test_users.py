from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import auth_headers, make_user


async def test_get_me_returns_user(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="me@test.com")
    r = await client.get("/users/me", headers=auth_headers(user))
    assert r.status_code == 200
    assert r.json()["email"] == "me@test.com"


async def test_get_me_returns_401_without_auth(client: AsyncClient):
    r = await client.get("/users/me")
    assert r.status_code == 401


async def test_update_me_changes_fields(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="upd@test.com")
    r = await client.patch(
        "/users/me",
        headers=auth_headers(user),
        json={"first_name": "Alice", "last_name": "Smith"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "Alice"
    assert body["last_name"] == "Smith"


async def test_update_me_returns_401_without_auth(client: AsyncClient):
    r = await client.patch("/users/me", json={"first_name": "X"})
    assert r.status_code == 401


async def test_delete_me_returns_204(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="del@test.com")
    r = await client.delete("/users/me", headers=auth_headers(user))
    assert r.status_code == 204


async def test_delete_me_returns_401_without_auth(client: AsyncClient):
    r = await client.delete("/users/me")
    assert r.status_code == 401