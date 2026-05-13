from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dto.transaction_dto import DepositDTO, WithdrawDTO
from exceptions.transaction import NotEnoughBalance
from services.user_transaction_service import UserTransactionService
from tests.factories import make_user


async def test_deposit_increases_balance(db: AsyncSession):
    user = await make_user(db, email="dep1@test.com")
    await UserTransactionService(db).deposit(user.id, DepositDTO(amount=Decimal("100.00")))
    assert user.balance == Decimal("100.00")


async def test_deposit_creates_transaction_record(db: AsyncSession):
    user = await make_user(db, email="dep2@test.com")
    tx = await UserTransactionService(db).deposit(
        user.id, DepositDTO(amount=Decimal("50.00"), description="top-up")
    )
    assert tx.id is not None
    assert tx.amount == Decimal("50.00")
    assert tx.type == "deposit"
    assert tx.description == "top-up"
    assert tx.user_id == user.id


async def test_multiple_deposits_accumulate(db: AsyncSession):
    user = await make_user(db, email="dep3@test.com")
    await UserTransactionService(db).deposit(user.id, DepositDTO(amount=Decimal("30.00")))
    await UserTransactionService(db).deposit(user.id, DepositDTO(amount=Decimal("20.00")))
    assert user.balance == Decimal("50.00")


async def test_withdraw_decreases_balance(db: AsyncSession):
    user = await make_user(db, email="wd1@test.com")
    svc = UserTransactionService(db)
    await svc.deposit(user.id, DepositDTO(amount=Decimal("100.00")))
    await svc.withdraw(user.id, WithdrawDTO(amount=Decimal("40.00")))
    assert user.balance == Decimal("60.00")


async def test_withdraw_creates_negative_transaction(db: AsyncSession):
    user = await make_user(db, email="wd2@test.com")
    svc = UserTransactionService(db)
    await svc.deposit(user.id, DepositDTO(amount=Decimal("100.00")))
    tx = await svc.withdraw(user.id, WithdrawDTO(amount=Decimal("25.00")))
    assert tx.amount == Decimal("-25.00")
    assert tx.type == "withdraw"


async def test_withdraw_raises_not_enough_balance(db: AsyncSession):
    user = await make_user(db, email="wd3@test.com")
    with pytest.raises(NotEnoughBalance):
        await UserTransactionService(db).withdraw(user.id, WithdrawDTO(amount=Decimal("1.00")))


async def test_withdraw_exact_balance_succeeds(db: AsyncSession):
    user = await make_user(db, email="wd4@test.com")
    svc = UserTransactionService(db)
    await svc.deposit(user.id, DepositDTO(amount=Decimal("50.00")))
    await svc.withdraw(user.id, WithdrawDTO(amount=Decimal("50.00")))
    assert user.balance == Decimal("0.00")


async def test_list_by_user_returns_transactions(db: AsyncSession):
    user = await make_user(db, email="lst1@test.com")
    svc = UserTransactionService(db)
    await svc.deposit(user.id, DepositDTO(amount=Decimal("10.00")))
    await svc.deposit(user.id, DepositDTO(amount=Decimal("20.00")))
    txs = await svc.list_by_user(user.id)
    assert len(txs) == 2


async def test_list_by_user_does_not_return_other_users(db: AsyncSession):
    u1 = await make_user(db, email="lst2a@test.com", username="lst2a")
    u2 = await make_user(db, email="lst2b@test.com", username="lst2b")
    svc = UserTransactionService(db)
    await svc.deposit(u1.id, DepositDTO(amount=Decimal("10.00")))
    await svc.deposit(u2.id, DepositDTO(amount=Decimal("10.00")))
    txs = await svc.list_by_user(u1.id)
    assert all(t.user_id == u1.id for t in txs)