from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_name: str
    price: Decimal
    duration_days: int


class CreateSubscriptionRequest(BaseModel):
    subscription_name: str
    price: Decimal
    duration_days: int


class UpdateSubscriptionRequest(BaseModel):
    subscription_name: str | None = None
    price: Decimal | None = None
    duration_days: int | None = None
