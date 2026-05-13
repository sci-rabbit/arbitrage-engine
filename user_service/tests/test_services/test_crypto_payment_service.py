import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.payment import PaymentProviderError
from services.crypto_payment_service import CryptoPaymentService
from tests.factories import make_crypto_payment, make_user


def _build_service(db: AsyncSession, *, configured: bool = True, ipn_secret: str = "test_secret") -> CryptoPaymentService:
    svc = CryptoPaymentService(db)
    svc.cfg = MagicMock(
        configured=configured,
        api_key="test_api_key",
        ipn_secret=ipn_secret,
        base_url="https://api.nowpayments.io",
    )
    return svc


def _make_sig(body: bytes, secret: str) -> str:
    data = json.loads(body)
    sorted_body = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret.encode(), sorted_body.encode(), hashlib.sha512).hexdigest()


# ---------------------------------------------------------------------------
# _verify_sig
# ---------------------------------------------------------------------------

def test_verify_sig_valid(db: AsyncSession):
    svc = _build_service(db)
    body = json.dumps({"payment_id": "123", "payment_status": "finished"}).encode()
    sig = _make_sig(body, "test_secret")
    assert svc._verify_sig(body, sig) is True


def test_verify_sig_invalid(db: AsyncSession):
    svc = _build_service(db)
    body = json.dumps({"payment_id": "123"}).encode()
    assert svc._verify_sig(body, "wrong_sig") is False


# ---------------------------------------------------------------------------
# get_currencies
# ---------------------------------------------------------------------------

async def test_get_currencies_raises_when_not_configured(db: AsyncSession):
    svc = _build_service(db, configured=False)
    with pytest.raises(PaymentProviderError):
        await svc.get_currencies()


async def test_get_currencies_returns_list(db: AsyncSession):
    svc = _build_service(db)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"currencies": ["btc", "eth"]}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("services.crypto_payment_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_currencies()

    assert result == ["btc", "eth"]


# ---------------------------------------------------------------------------
# handle_webhook
# ---------------------------------------------------------------------------

async def test_handle_webhook_raises_on_bad_sig(db: AsyncSession):
    svc = _build_service(db)
    body = json.dumps({"payment_id": "abc", "payment_status": "finished"}).encode()
    with pytest.raises(ValueError, match="Invalid signature"):
        await svc.handle_webhook(body, "bad_sig")


async def test_handle_webhook_credits_balance_on_finished(db: AsyncSession):
    user = await make_user(db, email="wh1@test.com")
    payment = await make_crypto_payment(
        db, user_id=user.id, nowpayments_id="pay_wh1",
        price_amount=Decimal("50.00"), payment_status="waiting",
    )
    svc = _build_service(db)
    svc._verify_sig = MagicMock(return_value=True)

    body = json.dumps({"payment_id": "pay_wh1", "payment_status": "finished"}).encode()
    await svc.handle_webhook(body, "any")

    assert user.balance == Decimal("50.00")
    assert payment.payment_status == "finished"


async def test_handle_webhook_does_not_double_credit(db: AsyncSession):
    user = await make_user(db, email="wh2@test.com")
    _payment = await make_crypto_payment(
        db, user_id=user.id, nowpayments_id="pay_wh2",
        price_amount=Decimal("50.00"), payment_status="finished",
    )
    svc = _build_service(db)
    svc._verify_sig = MagicMock(return_value=True)

    body = json.dumps({"payment_id": "pay_wh2", "payment_status": "finished"}).encode()
    await svc.handle_webhook(body, "any")

    assert user.balance == Decimal("0")


async def test_handle_webhook_skips_unknown_payment(db: AsyncSession):
    svc = _build_service(db)
    svc._verify_sig = MagicMock(return_value=True)

    body = json.dumps({"payment_id": "unknown_999", "payment_status": "finished"}).encode()
    await svc.handle_webhook(body, "any")
