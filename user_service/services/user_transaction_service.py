from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from dto.transaction_dto import DepositDTO, WithdrawDTO
from exceptions.transaction import NotEnoughBalance
from models.user_transaction import UserTransaction
from repositrories.user_repository import UserRepository
from repositrories.user_transaction_repository import UserTransactionRepository


class UserTransactionService:
    def __init__(self, session: AsyncSession):
        self.transaction_repo = UserTransactionRepository(session)
        self.user_repo = UserRepository(session)

    async def deposit(self, user_id: int, dto: DepositDTO) -> UserTransaction:
        user = await self.user_repo.get_for_update(user_id)

        user.balance += dto.amount

        return await self.transaction_repo.create_transaction(
            user_id=user_id,
            amount=dto.amount,
            type="deposit",
            description=dto.description,
        )

    async def withdraw(self, user_id: int, dto: WithdrawDTO) -> UserTransaction:
        user = await self.user_repo.get_for_update(user_id)

        if user.balance < dto.amount:
            raise NotEnoughBalance()

        user.balance -= dto.amount

        return await self.transaction_repo.create_transaction(
            user_id=user_id,
            amount=-dto.amount,
            type="withdraw",
            description=dto.description,
        )

    async def list_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserTransaction]:
        return await self.transaction_repo.get_by_user_id(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
