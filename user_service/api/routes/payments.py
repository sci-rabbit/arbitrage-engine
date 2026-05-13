from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser
from core.config import settings
from core.database import get_ro_session, get_rw_session
from schemas.payment import CreatePaymentRequest, PaymentResponse
from services.crypto_payment_service import CryptoPaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

RWSession = Annotated[AsyncSession, Depends(get_rw_session)]
ROSession = Annotated[AsyncSession, Depends(get_ro_session)]


@router.get("/currencies")
async def get_currencies(session: ROSession) -> list:
    return await CryptoPaymentService(session).get_currencies()


@router.post("/create", status_code=201, dependencies=[Depends(RateLimiter(times=5, hours=1))])
async def create_payment(
    current_user: CurrentUser,
    body: CreatePaymentRequest,
    request: Request,
    session: RWSession,
) -> PaymentResponse:
    base = settings.nowpayments.webhook_base_url.rstrip("/") or str(request.base_url).rstrip("/")
    callback_url = f"{base}/payments/webhook"
    return await CryptoPaymentService(session).create_payment(
        user_id=current_user.id,
        price_amount=body.amount,
        pay_currency=body.currency,
        callback_url=callback_url,
    )


@router.post("/webhook", status_code=200)
async def webhook(
    request: Request,
    session: RWSession,
    x_nowpayments_sig: str = Header(alias="x-nowpayments-sig"),
) -> dict:
    body = await request.body()
    try:
        await CryptoPaymentService(session).handle_webhook(body, x_nowpayments_sig)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    return {"status": "ok"}
