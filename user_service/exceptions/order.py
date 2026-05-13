from exceptions.base import BaseAppException


class OrderNotFound(BaseAppException):
    status_code = 404
    detail = "Order not found"
