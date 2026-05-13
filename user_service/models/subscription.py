from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import String, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


if TYPE_CHECKING:
    from models.order_product_association import OrderProductAssociation

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(primary_key=True)

    subscription_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    duration_days: Mapped[int] = mapped_column(Integer)

    orders_details: Mapped[list["OrderProductAssociation"]] = relationship(
        back_populates="subscription"
    )
