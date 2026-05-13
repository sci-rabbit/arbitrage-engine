from services.market_service.base_service import BaseService

services_storage = {}

def add_service(service: BaseService, platform: str) -> None:
    services_storage[platform] = service
