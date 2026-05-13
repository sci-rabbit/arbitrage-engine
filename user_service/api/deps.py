from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_ro_session
from core.security import decode_token
from exceptions.user import UserNotFound
from models.user import User
from services.user.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def require(*, access: bool = False, admin: bool = False):
    async def dependency(current_user: "CurrentUser") -> User:
        if access and not current_user.has_access:
            raise HTTPException(status_code=403, detail="Access required")
        if admin and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin required")
        return current_user
    return Depends(dependency)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_ro_session)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        return await UserService(session).get_by_id(int(user_id))
    except UserNotFound:
        raise credentials_exception


async def get_user_with_access(current_user: "CurrentUser") -> User:
    if not current_user.has_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return current_user


async def get_admin_user(current_user: "ActiveUser") -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_user_with_access)]
AdminUser = Annotated[User, Depends(get_admin_user)]
