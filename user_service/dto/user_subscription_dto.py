from dataclasses import dataclass
from datetime import datetime


@dataclass
class GrantSubscriptionDTO:
    user_id: int
    subscription_id: int
    expired_at: datetime


@dataclass
class ExtendSubscriptionDTO:
    days: int
