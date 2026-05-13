import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.getLogger(__name__)

class HealthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_database_online(self) -> bool:
        try:
            await self.session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("database.healthcheck.failed", error=str(e))
            return False