from typing import Any


def success_response(data: Any = None, message: str = "ok", code: int = 0) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def error_response(message: str, code: int, data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}

