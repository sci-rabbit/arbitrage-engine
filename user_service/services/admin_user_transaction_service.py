from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from models.user_transaction import UserTransaction
from services.user_transaction_service import UserTransactionService


class AdminUserTransactionService(UserTransactionService):

    async def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        type: str | None = None,
    ) -> List[UserTransaction]:
        return await self.transaction_repo.get_all(
            limit=limit,
            offset=offset,
            type=type,
        )
