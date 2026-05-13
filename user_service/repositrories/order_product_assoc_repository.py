import structlog

from models.order_product_association import OrderProductAssociation
from repositrories.base_repository import AsyncRepository

logger = structlog.getLogger(__name__)


class OrderProductAssocRepository(AsyncRepository[OrderProductAssociation]):
    model = OrderProductAssociation
