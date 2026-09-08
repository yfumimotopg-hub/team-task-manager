import logging

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.error_handlers import register_error_handlers
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)


class _EchoBody(BaseModel):
    name: str


class _IntOut(BaseModel):
    value: int


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    router = APIRouter()

    @router.get("/raise-not-found")
    def _raise_not_found() -> None:
        raise NotFoundError("THING_NOT_FOUND", "Thing not found")

    @router.get("/raise-conflict")
    def _raise_conflict() -> None:
        raise ConflictError("THING_TAKEN", "Thing already exists")

    @router.get("/raise-permission-denied")
    def _raise_permission_denied() -> None:
        raise PermissionDeniedError("PERMISSION_DENIED", "Not allowed")

    @router.get("/raise-base-app-error")
    def _raise_base_app_error() -> None:
        raise AppError("LEAKY_CODE", "leaky internal message")

    @router.post("/echo")
    def _echo(body: _EchoBody) -> _EchoBody:
        return body

    @router.get("/raise-runtime")
    def _raise_runtime() -> None:
        raise RuntimeError("boom secret-value 12345")

    @router.get("/bad-response", response_model=_IntOut)
    def _bad_response() -> dict[str, str]:
        return {"value": "not-an-int"}

    app.include_router(router)
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_app())


@pytest.fixture
def client_no_reraise() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


def test_not_found_error_returns_envelope(client: TestClient) -> None:
    response = client.get("/raise-not-found")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "THING_NOT_FOUND",
            "message": "Thing not found",
            "details": [],
        }
    }


def test_conflict_error_returns_409(client: TestClient) -> None:
    response = client.get("/raise-conflict")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "THING_TAKEN"


def test_permission_denied_error_returns_403(client: TestClient) -> None:
    response = client.get("/raise-permission-denied")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_base_app_error_returns_safe_500(client_no_reraise: TestClient) -> None:
    response = client_no_reraise.get("/raise-base-app-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": [],
        }
    }
    assert "LEAKY_CODE" not in response.text
    assert "leaky internal message" not in response.text


def test_request_validation_error_is_normalized(client: TestClient) -> None:
    response = client.post("/echo", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed"
    assert len(body["error"]["details"]) >= 1
    detail = body["error"]["details"][0]
    assert detail["field"] == "name"
    assert detail["code"] == "missing"
    assert isinstance(detail["message"], str)
    assert "detail" not in body  # FastAPI 既定の {"detail": [...]} を公開しない


def test_unhandled_exception_returns_safe_500(client_no_reraise: TestClient) -> None:
    response = client_no_reraise.get("/raise-runtime")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": [],
        }
    }
    assert "boom" not in response.text
    assert "secret-value" not in response.text
    assert "Traceback" not in response.text


def test_unhandled_exception_is_logged_server_side(
    client_no_reraise: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.core.error_handlers"):
        client_no_reraise.get("/raise-runtime")

    assert any(
        record.levelno >= logging.ERROR and record.exc_info is not None
        for record in caplog.records
    )


def test_response_validation_error_returns_safe_500(
    client_no_reraise: TestClient,
) -> None:
    response = client_no_reraise.get("/bad-response")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": [],
        }
    }


def test_unknown_route_404_is_normalized(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["details"] == []
    assert "detail" not in body


def test_method_not_allowed_405_is_normalized(client: TestClient) -> None:
    response = client.post("/raise-not-found")  # GET 専用ルート

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
