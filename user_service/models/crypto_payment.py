from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CryptoPayment(Base):
    __tablename__ = "crypto_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    nowpayments_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    pay_address: Mapped[str] = mapped_column(String, nullable=True)
    pay_currency: Mapped[str] = mapped_column(String)
    pay_amount: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=True)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_status: Mapped[str] = mapped_column(String, default="waiting")
