from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.mixin import UserRelationMixin

if TYPE_CHECKING:
    from models.order_product_association import (
        OrderProductAssociation,
    )

class Order(UserRelationMixin, Base):
    __tablename__ = 'orders'

    _user_id_nullable = True
    _user_id_unique = False
    _user_back_populates = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    products_details: Mapped[list["OrderProductAssociation"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
