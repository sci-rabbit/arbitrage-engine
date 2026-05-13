from decimal import Decimal
from typing import List

from sqlalchemy import select

from models.user_transaction import UserTransaction
from repositrories.base_repository import AsyncRepository


class UserTransactionRepository(AsyncRepository[UserTransaction]):
    model = UserTransaction

    async def create_transaction(
        self,
        user_id: int,
        amount: Decimal,
        type: str,
        description: str | None = None,
    ) -> UserTransaction:
        return await self.create(
            user_id=user_id,
            amount=amount,
            type=type,
            description=description,
        )

    async def get_by_user_id(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserTransaction]:
        stmt = (
            select(UserTransaction)
            .where(UserTransaction.user_id == user_id)
            .order_by(UserTransaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        type: str | None = None,
    ) -> List[UserTransaction]:
        stmt = select(UserTransaction).order_by(UserTransaction.id.desc())

        if type is not None:
            stmt = stmt.where(UserTransaction.type == type)

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
