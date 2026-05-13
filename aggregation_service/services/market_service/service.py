from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from core import Market
from services.market_service.kalshi_service import KalshiService
from services.market_service.polymarket_service import PolymarketService
from services.market_service.predictfun_service import PredictfunService
from services.market_service.service_storage import services_storage


class MarketService:
    def __init__(self, common_id: str, platform: str, session: AsyncSession,):
        self.common_id = common_id
        self.platform = platform
        self.session = session

    async def search(self) -> List[Market]:
        service = services_storage[self.platform](session=self.session)
        return await service.search(common_id=self.common_id)