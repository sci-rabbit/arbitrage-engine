from models.crypto_payment import CryptoPayment
from repositrories.base_repository import AsyncRepository


class CryptoPaymentRepository(AsyncRepository[CryptoPayment]):
    model = CryptoPayment
