from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in USD")
    currency: str = Field(..., description="Crypto currency code from GET /payments/currencies")

    @field_validator("currency")
    @classmethod
    def lowercase_currency(cls, v: str) -> str:
        return v.lower()


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nowpayments_id: str
    pay_address: str | None
    pay_currency: str
    pay_amount: Decimal | None
    price_amount: Decimal
    payment_status: str