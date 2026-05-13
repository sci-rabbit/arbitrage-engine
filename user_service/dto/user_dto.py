from dataclasses import dataclass


@dataclass
class CreateUserDTO:
    email: str
    password: str


@dataclass
class UpdateUserDTO:
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
