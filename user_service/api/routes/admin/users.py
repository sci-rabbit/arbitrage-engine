from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require
from core.database import get_ro_session, get_rw_session
from dto.user_dto import UpdateUserDTO
from schemas.user import UpdateUserRequest, UserResponse
from services.user.admin_user_service import AdminUserService

router = APIRouter(
    prefix="/users",
    tags=["admin:users"],
    dependencies=[require(admin=True)],
)

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("")
async def list_users(
    session: ROSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserResponse]:
    return await AdminUserService(session).list(limit=limit, offset=offset)


@router.get("/search")
async def search_users(
    session: ROSession,
    q: str = Query(min_length=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserResponse]:
    return await AdminUserService(session).search(q, limit=limit, offset=offset)


@router.get("/{user_id}")
async def get_user(user_id: int, session: ROSession) -> UserResponse:
    return await AdminUserService(session).get_by_id(user_id)


@router.patch("/{user_id}")
async def update_user(user_id: int, body: UpdateUserRequest, session: RWSession) -> UserResponse:
    service = AdminUserService(session)
    user = await service.get_by_id(user_id)
    return await service.update(user, UpdateUserDTO(**body.model_dump()))


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, session: RWSession) -> None:
    service = AdminUserService(session)
    user = await service.get_by_id(user_id)
    await service.delete(user)


@router.post("/{user_id}/grant-access")
async def grant_access(user_id: int, session: RWSession) -> UserResponse:
    service = AdminUserService(session)
    user = await service.get_by_id(user_id)
    return await service.grant_access(user)


@router.post("/{user_id}/revoke-access")
async def revoke_access(user_id: int, session: RWSession) -> UserResponse:
    service = AdminUserService(session)
    user = await service.get_by_id(user_id)
    return await service.revoke_access(user)
