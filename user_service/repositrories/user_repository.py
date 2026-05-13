
import structlog
from sqlalchemy import or_, select

from models.user import User
from repositrories.base_repository import AsyncRepository

logger = structlog.getLogger(__name__)


class UserRepository(AsyncRepository[User]):
    model = User

    async def get_for_update(self, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def search(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        stmt = (
            select(User)
            .where(
                or_(
                    User.email.ilike(f"%{query}%"),
                    User.username.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
