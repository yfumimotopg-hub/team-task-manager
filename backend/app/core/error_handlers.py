"""ADR-0006 準拠の共通 API エラーエンベロープへの変換。

すべての API エラーを ``{"error": {"code", "message", "details": []}}`` に統一する。
router に try/except を散らさず、ここで一元的に HTTP へ変換する。
"""

import logging
from collections.abc import Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.schemas.error import ErrorBody, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

_INTERNAL_ERROR_CODE = "INTERNAL_ERROR"
_INTERNAL_ERROR_MESSAGE = "Internal server error"
_VALIDATION_ERROR_CODE = "VALIDATION_ERROR"
_VALIDATION_ERROR_MESSAGE = "Request validation failed"

# RequestValidationError の loc 先頭に付く location タグ。field パスからは取り除く。
_LOC_PREFIXES = frozenset({"body", "query", "path", "header", "cookie"})

# framework/router 由来の HTTP エラーに与える安定コード。
# HTTPException を application/service 層のエラー手段にする意図ではなく、
# framework 由来のエラーを共通エンベロープから漏らさないための境界処理。
_HTTP_STATUS_CODES: dict[int, str] = {
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def _envelope(
    status_code: int,
    code: str,
    message: str,
    details: Sequence[ErrorDetail],
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=list(details))
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _internal_error_response() -> JSONResponse:
    return _envelope(500, _INTERNAL_ERROR_CODE, _INTERNAL_ERROR_MESSAGE, [])


def _field_from_loc(loc: Sequence[object]) -> str | None:
    parts = [str(part) for part in loc]
    if parts and parts[0] in _LOC_PREFIXES:
        parts = parts[1:]
    return ".".join(parts) if parts else None


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # handler は AppError 専用に登録される
        return await _handle_internal_error(request, exc)
    if exc.status_code >= 500:
        # 5xx（基底 AppError の誤用含む）は code / message を露出せず安全側に倒す。
        logger.error("AppError raised with 5xx status (code=%s)", exc.code)
        return _internal_error_response()
    return _envelope(exc.status_code, exc.code, exc.message, exc.details)


async def _handle_request_validation_error(
    request: Request, exc: Exception
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await _handle_internal_error(request, exc)
    details = [
        ErrorDetail(
            field=_field_from_loc(err.get("loc", ())),
            code=str(err.get("type", "")),
            message=str(err.get("msg", "")),
        )
        for err in exc.errors()
    ]
    return _envelope(422, _VALIDATION_ERROR_CODE, _VALIDATION_ERROR_MESSAGE, details)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return await _handle_internal_error(request, exc)
    code = _HTTP_STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if exc.detail is not None else _INTERNAL_ERROR_MESSAGE
    return _envelope(exc.status_code, code, message, [])


async def _handle_internal_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception during request %s %s", request.method, request.url.path
    )
    return _internal_error_response()


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_request_validation_error)
    app.add_exception_handler(ResponseValidationError, _handle_internal_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_internal_error)
