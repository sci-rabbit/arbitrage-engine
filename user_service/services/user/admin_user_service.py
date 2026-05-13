from typing import List

from models.user import User
from services.user.user_service import UserService


class AdminUserService(UserService):

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        **filters,
    ) -> List[User]:
        return await self.user_repo.paginate(limit=limit, offset=offset, **filters)

    async def search(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        return await self.user_repo.search(query, limit=limit, offset=offset)

    async def grant_access(self, user: User) -> User:
        return await self.user_repo.update(obj=user, obj_data={"has_access": True})

    async def revoke_access(self, user: User) -> User:
        return await self.user_repo.update(obj=user, obj_data={"has_access": False})