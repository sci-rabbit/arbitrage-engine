from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.order import Order
    from models.subscription import Subscription

class OrderProductAssociation(Base):
    __tablename__ = "order_product_association"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "sub_id",
            name="idx_unique_order_product",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    sub_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    count: Mapped[Decimal] = mapped_column(default=1, server_default="1")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="products_details")
    subscription: Mapped["Subscription"] = relationship(back_populates="orders_details")
