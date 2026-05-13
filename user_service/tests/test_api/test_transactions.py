from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from dto.transaction_dto import DepositDTO
from services.user_transaction_service import UserTransactionService
from tests.factories import auth_headers, make_user


# ---------------------------------------------------------------------------
# GET /transactions/my
# ---------------------------------------------------------------------------

async def test_my_transactions_returns_200(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="txlist@test.com")
    r = await client.get("/transactions/my", headers=auth_headers(user))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_my_transactions_returns_401_without_auth(client: AsyncClient):
    r = await client.get("/transactions/my")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /transactions/deposit
# ---------------------------------------------------------------------------

async def test_deposit_returns_201(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="dep@test.com")
    r = await client.post(
        "/transactions/deposit",
        headers=auth_headers(user),
        json={"amount": "50.00"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["type"] == "deposit"
    assert Decimal(body["amount"]) == Decimal("50.00")


async def test_deposit_returns_422_on_zero_amount(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="depzero@test.com")
    r = await client.post(
        "/transactions/deposit",
        headers=auth_headers(user),
        json={"amount": "0"},
    )
    assert r.status_code == 422


async def test_deposit_returns_422_on_negative_amount(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="depneg@test.com")
    r = await client.post(
        "/transactions/deposit",
        headers=auth_headers(user),
        json={"amount": "-10"},
    )
    assert r.status_code == 422


async def test_deposit_returns_401_without_auth(client: AsyncClient):
    r = await client.post("/transactions/deposit", json={"amount": "10"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /transactions/withdraw
# ---------------------------------------------------------------------------

async def test_withdraw_returns_201(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="wd@test.com")
    await UserTransactionService(db).deposit(user.id, DepositDTO(amount=Decimal("100.00")))
    r = await client.post(
        "/transactions/withdraw",
        headers=auth_headers(user),
        json={"amount": "30.00"},
    )
    assert r.status_code == 201
    assert Decimal(r.json()["amount"]) == Decimal("-30.00")


async def test_withdraw_returns_400_on_insufficient_funds(client: AsyncClient, db: AsyncSession):
    user = await make_user(db, email="wdlow@test.com")
    r = await client.post(
        "/transactions/withdraw",
        headers=auth_headers(user),
        json={"amount": "999.00"},
    )
    assert r.status_code == 400


async def test_withdraw_returns_401_without_auth(client: AsyncClient):
    r = await client.post("/transactions/withdraw", json={"amount": "10"})
    assert r.status_code == 401