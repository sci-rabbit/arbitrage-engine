from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.order import Order


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(
        String, nullable=True, unique=True, index=True
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_access: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    orders_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    subs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False)

    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
