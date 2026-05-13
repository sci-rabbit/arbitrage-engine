from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sub_id: int
    count: Decimal
    unit_price: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    products_details: list[OrderProductResponse]
