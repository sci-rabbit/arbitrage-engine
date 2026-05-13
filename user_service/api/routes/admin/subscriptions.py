from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require
from core.database import get_rw_session, get_ro_session
from dto.subscription_dto import CreateSubDTO, UpdateSubDTO
from schemas.subscription import SubscriptionResponse, CreateSubscriptionRequest, UpdateSubscriptionRequest
from services.subscription.admin_subscription_service import AdminSubscriptionService

router = APIRouter(
    prefix="/subscriptions",
    tags=["admin:subscriptions"],
    dependencies=[require(admin=True)],
)

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("")
async def list_subscriptions(
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[SubscriptionResponse]:
    return await AdminSubscriptionService(session).list(limit=limit, offset=offset)


@router.get("/{sub_id}")
async def get_subscription(sub_id: int, session: ROSession) -> SubscriptionResponse:
    return await AdminSubscriptionService(session).get_by_id(sub_id)


@router.post("", status_code=201)
async def create_subscription(body: CreateSubscriptionRequest, session: RWSession) -> SubscriptionResponse:
    return await AdminSubscriptionService(session).create_subscription(
        CreateSubDTO(**body.model_dump())
    )


@router.patch("/{sub_id}")
async def update_subscription(
    sub_id: int,
    body: UpdateSubscriptionRequest,
    session: RWSession,
) -> SubscriptionResponse:
    service = AdminSubscriptionService(session)
    sub = await service.get_by_id(sub_id)
    return await service.update_subscription(sub, UpdateSubDTO(**body.model_dump()))


@router.delete("/{sub_id}", status_code=204)
async def delete_subscription(sub_id: int, session: RWSession) -> None:
    service = AdminSubscriptionService(session)
    sub = await service.get_by_id(sub_id)
    await service.delete_subscription(sub)
