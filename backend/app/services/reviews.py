"""Match reviews: the open window (REV-001), public list and count (REV-004).

Reviews are text only: no star rating and no average; the list carries the valid review
count. Writing (create/edit/delete, one per member and match, body 1-300 characters)
belongs to chat 02 and must check `review_open` on the server before saving.

Popular order (REV-004 rule 5): reviews with at least 3 reactions first, by like ratio,
then likes, then newest; the rest after them, newest first. Latest order: newest first.
"""

from typing import Literal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.fixture import Fixture
from app.models.review import Review, ReviewReaction
from app.schemas.match_detail import ReviewItem, ReviewList, ReviewSummary

ReviewSort = Literal["popular", "latest"]
POPULAR_MIN_REACTIONS = 3
# Normal results only. Rulings (AWD/WO) stay closed (P-05, recommended option applied
# 2026-11-11: a result decided off the pitch is not reviewed), and abandoned/cancelled/
# changed matches hide their reviews until they are finished normally again (P-07).
REVIEWABLE_FINISH_TYPES = ("normal", "aet", "pen")
# Live codes closed like a stopped match (recommended option 2026-11-11): SUSP is a
# suspension whose resumption is uncertain (it often ends as ABD). INT, a short
# interruption inside the match, stays open. Reviews reappear when play resumes (P-07).
CLOSED_LIVE_CODES = frozenset({"SUSP"})


def review_open(fixture: Fixture) -> bool:
    """REV-001: reviews are read publicly and may be written from kickoff (live) to a
    normal finish, on the same match id, so a review written live stays after the finish.
    Closed: scheduled, postponed, cancelled, abandoned, suspended (SUSP), rulings (AWD/WO)
    and unknown. Open live codes: 1H·HT·2H·ET·BT·P·LIVE·INT."""
    if fixture.status == "live":
        return (fixture.status_short_raw or "").strip().upper() not in CLOSED_LIVE_CODES
    return fixture.status == "finished" and fixture.finish_type in REVIEWABLE_FINISH_TYPES


def list_reviews(session: Session, fixture_id: int, sort: ReviewSort) -> ReviewList:
    likes = func.count().filter(ReviewReaction.value == 1)
    dislikes = func.count().filter(ReviewReaction.value == -1)
    counts = (
        select(
            ReviewReaction.review_id.label("review_id"),
            likes.label("likes"),
            dislikes.label("dislikes"),
        )
        .group_by(ReviewReaction.review_id)
        .subquery()
    )
    like_count = func.coalesce(counts.c.likes, 0)
    dislike_count = func.coalesce(counts.c.dislikes, 0)
    total = like_count + dislike_count
    query = (
        select(Review, like_count, dislike_count)
        .outerjoin(counts, counts.c.review_id == Review.id)
        .where(Review.fixture_id == fixture_id)
    )
    if sort == "popular":
        enough = total >= POPULAR_MIN_REACTIONS
        ratio = case((enough, like_count * 1.0 / func.nullif(total, 0)), else_=None)
        query = query.order_by(
            case((enough, 0), else_=1),
            ratio.desc().nulls_last(),
            case((enough, like_count), else_=None).desc().nulls_last(),
            Review.created_at.desc(),
            Review.id.desc(),
        )
    else:
        query = query.order_by(Review.created_at.desc(), Review.id.desc())
    rows = session.execute(query).all()

    items = [
        ReviewItem(
            id=review.id,
            # `users` arrives with chat 02, which joins the nickname here.
            author_nickname=None,
            body=review.body,
            likes=int(up),
            dislikes=int(down),
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
        for review, up, down in rows
    ]
    return ReviewList(summary=ReviewSummary(count=len(items)), items=items)
