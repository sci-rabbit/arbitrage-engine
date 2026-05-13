from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require
from core.database import get_ro_session
from schemas.order import OrderResponse
from services.order_service import OrderService

router = APIRouter(
    tags=["admin:orders"],
    dependencies=[require(admin=True)],
)

ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("/users/{user_id}/orders")
async def list_user_orders(
    user_id: int,
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[OrderResponse]:
    return await OrderService(session).list_by_user(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/{order_id}")
async def get_order(order_id: int, session: ROSession) -> OrderResponse:
    return await OrderService(session).get_by_id(order_id)
