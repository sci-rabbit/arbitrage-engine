from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from core.database import get_rw_session, get_ro_session
from schemas.order import OrderResponse
from schemas.subscription import SubscriptionResponse
from schemas.user_subscription import UserSubscriptionResponse
from services.order_service import OrderService
from services.subscription.admin_subscription_service import AdminSubscriptionService
from services.subscription.subscription_service import SubscriptionService
from services.user_subscription_service import UserSubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("")
async def list_subscriptions(
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[SubscriptionResponse]:
    return await AdminSubscriptionService(session).list(limit=limit, offset=offset)


@router.post("/{sub_id}/buy", status_code=201)
async def buy_subscription(
    sub_id: int,
    current_user: CurrentUser,
    session: RWSession,
    count: int = Query(1, ge=1),
) -> OrderResponse:
    admin_service = AdminSubscriptionService(session)
    subscription = await admin_service.get_by_id(sub_id)
    return await SubscriptionService(session).buy_subscription(
        user_id=current_user.id,
        subscription=subscription,
        count=count,
    )


@router.get("/my")
async def my_subscriptions(
    current_user: CurrentUser,
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[UserSubscriptionResponse]:
    return await UserSubscriptionService(session).list_active(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/my/orders")
async def my_orders(
    current_user: CurrentUser,
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[OrderResponse]:
    return await OrderService(session).list_by_user(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
