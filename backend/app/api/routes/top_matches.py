from fastapi import APIRouter

from app.schemas.common import DataResponse
from app.schemas.top_matches import TopMatches
from app.services.top_matches import get_current_top_matches

router = APIRouter(prefix="/top-matches", tags=["top-matches"])


@router.get("/current")
def read_current_top_matches() -> DataResponse[TopMatches]:
    # meta.updatedAt is the last selection time; null until chat 04 computes rankings.
    return DataResponse(data=get_current_top_matches(), meta={"updatedAt": None})
