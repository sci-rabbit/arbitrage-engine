import structlog
from sqlalchemy.orm.attributes import set_committed_value

from models.order import Order
from models.order_product_association import OrderProductAssociation
from models.subscription import Subscription
from repositrories.base_repository import AsyncRepository

logger = structlog.getLogger(__name__)


class OrderRepository(AsyncRepository[Order]):
    model = Order

    async def create_order(
        self,
        user_id: int,
        subscription: Subscription,
        count: int,
    ) -> Order:
        order = Order(user_id=user_id)
        self.session.add(order)
        await self.session.flush()

        assoc = OrderProductAssociation(
            order_id=order.id,
            sub_id=subscription.id,
            count=count,
            unit_price=subscription.price,
        )
        self.session.add(assoc)
        await self.session.flush()

        set_committed_value(order, "products_details", [assoc])
        return order
