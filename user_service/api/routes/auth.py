from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from core.database import get_rw_session
from core.security import create_token, decode_token, verify_password
from dto.user_dto import CreateUserDTO
from exceptions.user import UserNotFound
from schemas.auth import ForgotPasswordRequest, LoginRequest, RefreshRequest, ResetPasswordRequest
from schemas.user import UserResponse, RegisterRequest
from services.email_service import send_reset_password_email, send_verification_email
from services.user.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    session: RWSession,
) -> UserResponse:
    user = await UserService(session).create(CreateUserDTO(email=body.email, password=body.password))
    await session.commit()
    background_tasks.add_task(send_verification_email, user.email)
    return user


@router.post("/login", dependencies=[Depends(RateLimiter(times=10, minutes=15))])
async def login(
    body: LoginRequest,
    session: RWSession,
):
    service = UserService(session)
    try:
        user = await service.get_by_email(body.email)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {
        "access_token": create_token(user.id, "access", extra_claims={"has_access": user.has_access}),
        "refresh_token": create_token(user.id, "refresh"),
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(body: RefreshRequest, session: RWSession) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user = await UserService(session).get_by_id(int(user_id))
    except Exception:
        raise credentials_exception

    return {
        "access_token": create_token(user_id, "access", extra_claims={"has_access": user.has_access}),
        "token_type": "bearer",
    }


@router.post("/resend-verification")
async def resend_verification(
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> dict:
    if current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")
    background_tasks.add_task(send_verification_email, current_user.email)
    return {"detail": "Verification email sent"}


@router.get("/verify")
async def verify_email(
    token: str,
    session: RWSession,
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification link",
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "verify":
            raise credentials_exception
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user = await UserService(session).get_by_email(email)
    except UserNotFound:
        raise credentials_exception

    if not user.is_verified:
        await UserService(session).set_verified(user)

    return {"detail": "Email verified successfully"}


@router.post("/forgot-password", dependencies=[Depends(RateLimiter(times=3, minutes=15))])
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: RWSession,
) -> dict:
    try:
        await UserService(session).get_by_email(body.email)
        background_tasks.add_task(send_reset_password_email, body.email)
    except UserNotFound:
        pass
    return {"detail": "If this email is registered, you will receive a reset link"}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    session: RWSession,
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset link",
    )
    try:
        payload = decode_token(body.token)
        if payload.get("type") != "reset":
            raise credentials_exception
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user = await UserService(session).get_by_email(email)
    except UserNotFound:
        raise credentials_exception

    await UserService(session).set_password(user, body.new_password)
    return {"detail": "Password updated successfully"}