from fastapi import FastAPI

from app.api.v1 import router as api_v1_router
from app.core.error_handlers import register_error_handlers

app = FastAPI(title="team-task-manager")
register_error_handlers(app)
app.include_router(api_v1_router, prefix="/api/v1")
