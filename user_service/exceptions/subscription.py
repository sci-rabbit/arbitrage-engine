from exceptions.base import BaseAppException


class SubscriptionAlreadyExists(BaseAppException):
    status_code = 409
    detail = "Subscription already exists"


class SubscriptionNotFound(BaseAppException):
    status_code = 404
    detail = "Subscription not found"
