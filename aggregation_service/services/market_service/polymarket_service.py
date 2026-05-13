from typing import List

from core import Market
from core.repositories.polymarket_repository import PolymarketRepository
from services.market_service.base_service import BaseService
from services.market_service.service_storage import add_service


class PolymarketService(BaseService):
    def __init__(self, session):
        self.session = session
        self.repo = PolymarketRepository(session=self.session)

    async def search(self, common_id) -> List[Market]:
        return await self.repo.search(common_id=common_id)


add_service(PolymarketService, platform="polymarket")