from exceptions.base import BaseAppException


class PaymentProviderError(BaseAppException):
    status_code = 502
    detail = "Payment provider error"


class PaymentProviderUnavailable(BaseAppException):
    status_code = 503
    detail = "Payment provider unavailable"
