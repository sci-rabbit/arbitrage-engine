from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from dto.user_dto import CreateUserDTO, UpdateUserDTO
from exceptions.user import UserAlreadyExists, UserNotFound
from models.user import User
from repositrories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def _get_or_raise(self, **filters) -> User:
        user = await self.user_repo.get_one_by(**filters)
        if user is None:
            raise UserNotFound()
        return user

    async def create(self, user_dto: CreateUserDTO):
        existing = await self.user_repo.get_one_by(email=user_dto.email)
        if existing:
            raise UserAlreadyExists()

        hashed_password = hash_password(user_dto.password)

        try:
            user = await self.user_repo.create(
                email=user_dto.email,
                password=hashed_password,
            )
            return user
        except IntegrityError:
            raise UserAlreadyExists()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._get_or_raise(id=user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._get_or_raise(email=email)

    async def update(self, user: User, user_dto: UpdateUserDTO) -> User:
        user_data = {k: v for k, v in user_dto.__dict__.items() if v is not None}

        if "password" in user_data:
            user_data["password"] = hash_password(user_data["password"])

        return await self.user_repo.update(obj=user, obj_data=user_data)

    async def set_verified(self, user: User) -> None:
        await self.user_repo.update(obj=user, obj_data={"is_verified": True})

    async def set_password(self, user: User, new_password: str) -> None:
        await self.user_repo.update(obj=user, obj_data={"password": hash_password(new_password)})

    async def delete(self, user: User) -> None:
        await self.user_repo.delete(obj=user)