from fastapi import APIRouter

from app.schemas.common import DataResponse
from app.schemas.top_matches import TopMatches
from app.services.top_matches import get_current_top_matches

router = APIRouter(prefix="/top-matches", tags=["top-matches"])


@router.get("/current")
def read_current_top_matches() -> DataResponse[TopMatches]:
    # data.selectedAt is the selection time; meta.updatedAt is the last match-data sync
    # (guide §6.4), null until chat 03/04 fill the items with collected matches.
    return DataResponse(data=get_current_top_matches(), meta={"updatedAt": None})
