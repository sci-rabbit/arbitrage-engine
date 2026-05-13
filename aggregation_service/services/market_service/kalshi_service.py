
from core import Market
from core.repositories.kalshi_repository import KalshiRepository
from services.market_service.base_service import BaseService
from services.market_service.service_storage import add_service


class KalshiService(BaseService):
    def __init__(self, session):
        self.session = session
        self.repo = KalshiRepository(session=self.session)

    async def search(self, common_id) -> list[Market]:
        return await self.repo.search(common_id=common_id.upper())


add_service(KalshiService, platform="kalshi")
