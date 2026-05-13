from exceptions.base import BaseAppException


class UserSubscriptionNotFound(BaseAppException):
    status_code = 404
    detail = "User subscription not found"
