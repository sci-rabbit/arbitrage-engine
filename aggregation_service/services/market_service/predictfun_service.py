
from core import Market
from core.repositories.predictfun_repository import PredictfunRepository
from services.market_service.base_service import BaseService
from services.market_service.service_storage import add_service


class PredictfunService(BaseService):
    def __init__(self, session):
        self.session = session
        self.repo = PredictfunRepository(session=self.session)

    async def search(self, common_id) -> list[Market]:
        return await self.repo.search(common_id=common_id)


add_service(PredictfunService, platform="predict_fun")
