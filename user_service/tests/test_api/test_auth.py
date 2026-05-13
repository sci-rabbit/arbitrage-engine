from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_token, decode_token
from tests.factories import make_user


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

async def test_register_returns_201(client: AsyncClient):
    r = await client.post("/auth/register", json={"email": "new@test.com", "password": "secret123"})
    assert r.status_code == 201
    assert r.json()["email"] == "new@test.com"


async def test_register_returns_409_on_duplicate(client: AsyncClient, db: AsyncSession):
    await make_user(db, email="dup@test.com")
    r = await client.post("/auth/register", json={"email": "dup@test.com", "password": "x"})
    assert r.status_code == 409


async def test_register_returns_422_on_invalid_email(client: AsyncClient):
    r = await client.post("/auth/register", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

async def test_login_returns_tokens(client: AsyncClient, db: AsyncSession):
    await make_user(db, email="login@test.com", password="pass123")
    r = await client.post("/auth/login", json={"email": "login@test.com", "password": "pass123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_returns_401_on_wrong_password(client: AsyncClient, db: AsyncSession):
    await make_user(db, email="wrong@test.com", password="correct")
    r = await client.post("/auth/login", json={"email": "wrong@test.com", "password": "wrong"})
    assert r.status_code == 401


async def test_login_returns_401_on_unknown_email(client: AsyncClient):
    r = await client.post("/auth/login", json={"email": "ghost@test.com", "password": "x"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

async def test_refresh_returns_new_access_token(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="ref@test.com")
    token = create_token(user.id, "refresh")
    r = await client.post("/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_refresh_includes_has_access_in_token(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="refaccess@test.com", has_access=True)
    token = create_token(user.id, "refresh")
    r = await client.post("/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 200
    payload = decode_token(r.json()["access_token"])
    assert payload["has_access"] is True


async def test_refresh_returns_401_on_invalid_token(client: AsyncClient):
    r = await client.post("/auth/refresh", json={"refresh_token": "not.a.token"})
    assert r.status_code == 401


async def test_refresh_returns_401_on_access_token(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="refwrong@test.com")
    access = create_token(user.id, "access")
    r = await client.post("/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/verify
# ---------------------------------------------------------------------------

async def test_verify_email_returns_200(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="verify@test.com", is_verified=False)
    token = create_token(user.email, "verify")
    r = await client.get(f"/auth/verify?token={token}")
    assert r.status_code == 200


async def test_verify_returns_400_on_invalid_token(client: AsyncClient):
    r = await client.get("/auth/verify?token=bad.token.here")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------

async def test_forgot_password_always_returns_200(client: AsyncClient):
    r = await client.post("/auth/forgot-password", json={"email": "anyone@test.com"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------

async def test_reset_password_returns_200(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="reset@test.com")
    token = create_token(user.email, "reset")
    r = await client.post("/auth/reset-password", json={"token": token, "new_password": "newpass"})
    assert r.status_code == 200


async def test_reset_password_returns_400_on_invalid_token(client: AsyncClient):
    r = await client.post("/auth/reset-password", json={"token": "bad.token", "new_password": "x"})
    assert r.status_code == 400