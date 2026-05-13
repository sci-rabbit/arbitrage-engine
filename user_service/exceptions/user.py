from exceptions.base import BaseAppException


class UserNotFound(BaseAppException):
    status_code = 404
    detail = "User not found"


class UserAlreadyExists(BaseAppException):
    status_code = 409
    detail = "User already exists"
