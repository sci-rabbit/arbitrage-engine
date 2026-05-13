from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from core.database import get_rw_session, get_ro_session
from dto.transaction_dto import DepositDTO, WithdrawDTO
from schemas.transaction import TransactionResponse, DepositRequest, WithdrawRequest
from services.user_transaction_service import UserTransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("/my")
async def my_transactions(
    current_user: CurrentUser,
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[TransactionResponse]:
    return await UserTransactionService(session).list_by_user(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.post("/deposit", status_code=201)
async def deposit(
    current_user: CurrentUser,
    body: DepositRequest,
    session: RWSession,
) -> TransactionResponse:
    return await UserTransactionService(session).deposit(
        user_id=current_user.id,
        dto=DepositDTO(amount=body.amount, description=body.description),
    )


@router.post("/withdraw", status_code=201)
async def withdraw(
    current_user: CurrentUser,
    body: WithdrawRequest,
    session: RWSession,
) -> TransactionResponse:
    return await UserTransactionService(session).withdraw(
        user_id=current_user.id,
        dto=WithdrawDTO(amount=body.amount, description=body.description),
    )
