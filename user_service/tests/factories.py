"""
Test data factories. Все функции делают flush (не commit) —
роллбэк в db-фикстуре всё уберёт.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_token, hash_password
from models.crypto_payment import CryptoPayment
from models.order import Order
from models.subscription import Subscription
from models.user import User
from models.user_subscriptions import UserSubscription


async def make_user(
    session: AsyncSession,
    *,
    email: str = "user@example.com",
    password: str = "password123",
    username: str | None = None,
    first_name: str = "Test",
    last_name: str = "User",
    is_verified: bool = True,
    is_active: bool = True,
    has_access: bool = False,
    is_admin: bool = False,
) -> User:
    user = User(
        email=email,
        password=hash_password(password),
        username=username or email.split("@")[0],
        first_name=first_name,
        last_name=last_name,
        is_verified=is_verified,
        is_active=is_active,
        has_access=has_access,
        is_admin=is_admin,
    )
    session.add(user)
    await session.flush()
    return user


async def make_user_with_access(session: AsyncSession, **kwargs) -> User:
    return await make_user(session, has_access=True, **kwargs)


async def make_admin(session: AsyncSession, **kwargs) -> User:
    return await make_user(session, is_admin=True, has_access=True, **kwargs)


def access_token(user: User) -> str:
    return create_token(user.id, "access", extra_claims={"has_access": user.has_access})


def auth_headers(user: User) -> dict:
    return {"Authorization": f"Bearer {access_token(user)}"}


async def make_subscription(
    session: AsyncSession,
    *,
    name: str = "Test Plan",
    price: Decimal = Decimal("9.99"),
    duration_days: int = 30,
) -> Subscription:
    sub = Subscription(subscription_name=name, price=price, duration_days=duration_days)
    session.add(sub)
    await session.flush()
    return sub


async def make_user_subscription(
    session: AsyncSession,
    *,
    user_id: int,
    subscription_id: int,
    expired_at: datetime | None = None,
    is_active: bool = True,
) -> UserSubscription:
    user_sub = UserSubscription(
        user_id=user_id,
        subscription_id=subscription_id,
        started_at=datetime.now(UTC),
        expired_at=expired_at or datetime.now(UTC) + timedelta(days=30),
        is_active=is_active,
    )
    session.add(user_sub)
    await session.flush()
    return user_sub


async def make_order(session: AsyncSession, *, user_id: int) -> Order:
    order = Order(user_id=user_id)
    session.add(order)
    await session.flush()
    return order


async def make_crypto_payment(
    session: AsyncSession,
    *,
    user_id: int,
    nowpayments_id: str = "pay_test_001",
    price_amount: Decimal = Decimal("10.00"),
    payment_status: str = "waiting",
    pay_currency: str = "btc",
) -> CryptoPayment:
    payment = CryptoPayment(
        user_id=user_id,
        nowpayments_id=nowpayments_id,
        pay_currency=pay_currency,
        price_amount=price_amount,
        payment_status=payment_status,
    )
    session.add(payment)
    await session.flush()
    return payment
