from fastapi import APIRouter, Depends

from app.api.deps import require_csrf
from app.api.routes import feedback, top_matches
from app.schemas.common import ErrorResponse

# Every /api/v1 route documents the shared error envelope and checks CSRF on changes.
api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_csrf)],
    responses={
        "4XX": {"model": ErrorResponse, "description": "Client error"},
        "5XX": {"model": ErrorResponse, "description": "Server error"},
    },
)
api_router.include_router(feedback.router)
api_router.include_router(top_matches.router)
