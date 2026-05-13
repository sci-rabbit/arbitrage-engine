import hashlib
import hmac
import json
from decimal import Decimal

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from exceptions.payment import PaymentProviderError, PaymentProviderUnavailable
from models.crypto_payment import CryptoPayment
from repositrories.crypto_payment_repository import CryptoPaymentRepository
from repositrories.user_repository import UserRepository

logger = structlog.getLogger(__name__)


class CryptoPaymentService:
    def __init__(self, session: AsyncSession):
        self.payment_repo = CryptoPaymentRepository(session)
        self.user_repo = UserRepository(session)
        self.cfg = settings.nowpayments

    def _check_configured(self) -> None:
        if not self.cfg.configured:
            raise PaymentProviderError()

    async def get_currencies(self) -> list[dict]:
        self._check_configured()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.nowpayments.io/v1/currencies",
                    headers={"x-api-key": self.cfg.api_key},
                    timeout=10.0,
                )
                resp.raise_for_status()
            return resp.json().get("currencies", [])
        except httpx.TimeoutException:
            raise PaymentProviderUnavailable()
        except httpx.HTTPStatusError as e:
            logger.error("NOWPayments get_currencies failed", status=e.response.status_code)
            raise PaymentProviderError()

    async def create_payment(
        self,
        user_id: int,
        price_amount: Decimal,
        pay_currency: str,
        callback_url: str,
    ) -> CryptoPayment:
        self._check_configured()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.cfg.base_url}/v1/payment",
                    headers={"x-api-key": self.cfg.api_key},
                    json={
                        "price_amount": float(price_amount),
                        "price_currency": "usd",
                        "pay_currency": pay_currency,
                        "order_description": f"Balance top-up for user {user_id}",
                        "ipn_callback_url": callback_url,
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            raise PaymentProviderUnavailable()
        except httpx.HTTPStatusError as e:
            logger.error("NOWPayments create_payment failed", status=e.response.status_code)
            raise PaymentProviderError()

        return await self.payment_repo.create(
            user_id=user_id,
            nowpayments_id=str(data["payment_id"]),
            pay_address=data.get("pay_address"),
            pay_currency=data["pay_currency"],
            pay_amount=data.get("pay_amount"),
            price_amount=price_amount,
            payment_status=data["payment_status"],
        )

    async def handle_webhook(self, body: bytes, sig: str) -> None:
        if not self._verify_sig(body, sig):
            raise ValueError("Invalid signature")

        data = json.loads(body)
        payment_id = str(data["payment_id"])
        new_status = data["payment_status"]

        payment = await self.payment_repo.get_one_by(nowpayments_id=payment_id)
        if payment is None:
            logger.warning("Webhook for unknown payment", payment_id=payment_id)
            return

        if new_status == "finished" and payment.payment_status != "finished":
            user = await self.user_repo.get_for_update(payment.user_id)
            user.balance += payment.price_amount
            logger.info(
                "Crypto payment finished, balance credited",
                user_id=payment.user_id,
                amount=payment.price_amount,
            )

        await self.payment_repo.update(payment, {"payment_status": new_status})

    def _verify_sig(self, body: bytes, sig: str) -> bool:
        data = json.loads(body)
        sorted_body = json.dumps(data, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(
            self.cfg.ipn_secret.encode(),
            sorted_body.encode(),
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, sig)
