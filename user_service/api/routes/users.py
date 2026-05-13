from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from core.database import get_rw_session
from dto.user_dto import UpdateUserDTO
from schemas.user import UserResponse, UserUpdateRequest
from services.user.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]


@router.get("/me")
async def get_me(current_user: CurrentUser) -> UserResponse:
    return current_user


@router.patch("/me")
async def update_me(
    current_user: CurrentUser,
    body: UserUpdateRequest,
    session: RWSession,
) -> UserResponse:
    return await UserService(session).update(
        current_user,
        UpdateUserDTO(**body.model_dump()),
    )


@router.delete("/me", status_code=204)
async def delete_me(current_user: CurrentUser, session: RWSession) -> None:
    await UserService(session).delete(current_user)
