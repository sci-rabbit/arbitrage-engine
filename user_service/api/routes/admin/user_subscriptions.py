from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require
from core.database import get_rw_session, get_ro_session
from dto.user_subscription_dto import GrantSubscriptionDTO, ExtendSubscriptionDTO
from schemas.user_subscription import UserSubscriptionResponse, GrantSubscriptionRequest, ExtendSubscriptionRequest
from services.admin_user_subscription_service import AdminUserSubscriptionService

router = APIRouter(
    prefix="/users/{user_id}/subscriptions",
    tags=["admin:user-subscriptions"],
    dependencies=[require(admin=True)],
)

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("")
async def list_user_subscriptions(
    user_id: int,
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[UserSubscriptionResponse]:
    return await AdminUserSubscriptionService(session).list_all_by_user(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=201)
async def grant_subscription(
    user_id: int,
    body: GrantSubscriptionRequest,
    session: RWSession,
) -> UserSubscriptionResponse:
    return await AdminUserSubscriptionService(session).grant(
        GrantSubscriptionDTO(
            user_id=user_id,
            subscription_id=body.subscription_id,
            expired_at=body.expired_at,
        )
    )


@router.patch("/{subscription_id}")
async def extend_subscription(
    user_id: int,
    subscription_id: int,
    body: ExtendSubscriptionRequest,
    session: RWSession,
) -> UserSubscriptionResponse:
    return await AdminUserSubscriptionService(session).extend(
        user_id=user_id,
        subscription_id=subscription_id,
        dto=ExtendSubscriptionDTO(days=body.days),
    )


@router.delete("/{subscription_id}", status_code=204)
async def revoke_subscription(
    user_id: int,
    subscription_id: int,
    session: RWSession,
) -> None:
    await AdminUserSubscriptionService(session).revoke(
        user_id=user_id,
        subscription_id=subscription_id,
    )
