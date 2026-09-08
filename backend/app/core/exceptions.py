from typing import ClassVar

from app.schemas.error import ErrorDetail


class AppError(Exception):
    """アプリ内で扱う想定内エラーの基底。

    service / repository はこの階層を送出し、HTTP を意識しない。
    HTTP への変換は exception handler が行う（app/core/error_handlers.py）。
    """

    status_code: ClassVar[int] = 500

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details: list[ErrorDetail] = details if details is not None else []


class NotFoundError(AppError):
    status_code: ClassVar[int] = 404


class ConflictError(AppError):
    status_code: ClassVar[int] = 409


class PermissionDeniedError(AppError):
    status_code: ClassVar[int] = 403
