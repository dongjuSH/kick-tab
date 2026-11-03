from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.top_matches import (
    TopMatchesMeta,
    TopMatchesResponse,
    TopMatchesVersionResponse,
)
from app.services.top_matches import current_version, get_current_top_matches

router = APIRouter(prefix="/top-matches", tags=["top-matches"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/current")
def read_current_top_matches(db: Db) -> TopMatchesResponse:
    # data.selectedAt is the selection time; meta.updatedAt is the last provider sync of the
    # listed matches (guide §6.4). Reading never starts a selection.
    data, updated_at = get_current_top_matches(db, datetime.now(UTC))
    return TopMatchesResponse(data=data, meta=TopMatchesMeta(updated_at=updated_at))


@router.get("/version")
def read_top_matches_version(db: Db) -> TopMatchesVersionResponse:
    """Public version only, polled by open screens to replace the list right away."""
    return TopMatchesVersionResponse(data=current_version(db, datetime.now(UTC)))
