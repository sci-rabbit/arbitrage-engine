from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None
    first_name: str | None
    last_name: str | None
    is_active: bool
    is_verified: bool
    has_access: bool
    is_admin: bool
    balance: Decimal
    orders_count: int
    subs_count: int


class UpdateUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    has_access: bool | None = None
