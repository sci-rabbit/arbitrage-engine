import structlog

from models.subscription import Subscription
from repositrories.base_repository import AsyncRepository

logger = structlog.getLogger(__name__)


class SubscriptionRepository(AsyncRepository[Subscription]):
    model = Subscription
