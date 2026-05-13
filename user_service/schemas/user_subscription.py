from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    subscription_id: int
    started_at: datetime
    expired_at: datetime
    is_active: bool


class GrantSubscriptionRequest(BaseModel):
    subscription_id: int
    expired_at: datetime


class ExtendSubscriptionRequest(BaseModel):
    days: int
