"""feature router が `responses=` に spread して使う共通のエラーレスポンス定義。

ADR-0006 の共通 `ErrorResponse` を OpenAPI に明示するための最小の仕組み。
"""

from typing import Any

from app.schemas.error import ErrorResponse

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": "Permission denied"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}
