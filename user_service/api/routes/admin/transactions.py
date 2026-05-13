from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require
from core.database import get_rw_session, get_ro_session
from dto.transaction_dto import DepositDTO, WithdrawDTO
from schemas.transaction import TransactionResponse, DepositRequest, WithdrawRequest
from services.admin_user_transaction_service import AdminUserTransactionService

router = APIRouter(
    tags=["admin:transactions"],
    dependencies=[require(admin=True)],
)

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("/transactions")
async def list_all_transactions(
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type: str | None = Query(None, pattern="^(deposit|withdraw|purchase)$"),
) -> List[TransactionResponse]:
    return await AdminUserTransactionService(session).list_all(
        limit=limit,
        offset=offset,
        type=type,
    )


@router.get("/users/{user_id}/transactions")
async def list_user_transactions(
    user_id: int,
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[TransactionResponse]:
    return await AdminUserTransactionService(session).list_by_user(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.post("/users/{user_id}/transactions/deposit", status_code=201)
async def deposit(user_id: int, body: DepositRequest, session: RWSession) -> TransactionResponse:
    return await AdminUserTransactionService(session).deposit(
        user_id=user_id,
        dto=DepositDTO(amount=body.amount, description=body.description),
    )


@router.post("/users/{user_id}/transactions/withdraw", status_code=201)
async def withdraw(user_id: int, body: WithdrawRequest, session: RWSession) -> TransactionResponse:
    return await AdminUserTransactionService(session).withdraw(
        user_id=user_id,
        dto=WithdrawDTO(amount=body.amount, description=body.description),
    )
