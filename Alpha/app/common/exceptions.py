class AppException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def bad_request(message: str = "bad request", code: int = 40000) -> AppException:
    return AppException(code=code, message=message, status_code=400)


def unauthorized(message: str = "unauthorized", code: int = 40003) -> AppException:
    return AppException(code=code, message=message, status_code=401)


def forbidden(message: str = "forbidden", code: int = 40003) -> AppException:
    return AppException(code=code, message=message, status_code=403)


def not_found(message: str = "not found", code: int = 40004) -> AppException:
    return AppException(code=code, message=message, status_code=404)


def conflict(message: str = "conflict", code: int = 40009) -> AppException:
    return AppException(code=code, message=message, status_code=409)

