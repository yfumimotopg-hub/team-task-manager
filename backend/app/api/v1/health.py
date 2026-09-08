from fastapi import APIRouter

from app.api.errors import ERROR_RESPONSES
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: ERROR_RESPONSES[500]},
)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")
