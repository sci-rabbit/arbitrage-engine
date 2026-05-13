from exceptions.base import BaseAppException


class NotEnoughBalance(BaseAppException):
    status_code = 400
    detail = "Not enough balance"
