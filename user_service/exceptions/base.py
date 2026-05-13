class BaseAppException(Exception):
    status_code = 500
    detail = "Internal server error"


class NotFound(BaseAppException):
    status_code = 404
    detail = "Object not found"