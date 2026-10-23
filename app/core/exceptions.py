from typing import Any


class AppException(Exception):
    status_code = 500
    code = "app_error"

    def __init__(self, detail: str = "Application error", *, code: str | None = None, extra: Any = None):
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code
        self.extra = extra


class BadRequestError(AppException):
    status_code = 400
    code = "bad_request"


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"


class InvalidTransitionError(ConflictError):
    code = "invalid_status_transition"
