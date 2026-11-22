"""Match reviews: the open window (REV-001), public list and count (REV-004), and the
member writing side (chat 02, REV-002·003).

Reviews are text only: no star rating and no average; the list carries the valid review
count. Writing: one per member and match, body 1-300 characters and not only spaces,
created/edited and reacted to only while `review_open`; reactions one per member and
review, never on one's own. A member may delete their own review at any time.

Popular order (REV-004 rule 5): reviews with at least 3 reactions first, by like ratio,
then likes, then newest; the rest after them, newest first. Latest order: newest first.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.kst import KST
from app.models.fixture import Fixture
from app.models.reference import Competition, Team
from app.models.review import REVIEW_BODY_MAX, Review, ReviewReaction
from app.models.user import User
from app.schemas.match_detail import MyReview, ReviewItem, ReviewList, ReviewSummary
from app.services.fixtures import to_summary
from app.services.reference import team_detail_lookup

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

CLOSED = "지금은 이 경기의 평가를 작성·수정할 수 없습니다."
REVIEW_NOT_FOUND = "평가를 찾을 수 없습니다. 목록을 새로 불러와 주세요."


def review_open(fixture: Fixture) -> bool:
    """REV-001: reviews are read publicly and may be written from kickoff (live) to a
    normal finish, on the same match id, so a review written live stays after the finish.
    Closed: scheduled, postponed, cancelled, abandoned, suspended (SUSP), rulings (AWD/WO)
    and unknown. Open live codes: 1H·HT·2H·ET·BT·P·LIVE·INT."""
    if fixture.status == "live":
        return (fixture.status_short_raw or "").strip().upper() not in CLOSED_LIVE_CODES
    return fixture.status == "finished" and fixture.finish_type in REVIEWABLE_FINISH_TYPES


def _counts():
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
    return counts, func.coalesce(counts.c.likes, 0), func.coalesce(counts.c.dislikes, 0)


def _item(
    review: Review,
    nickname: str | None,
    likes: int,
    dislikes: int,
    viewer: uuid.UUID | None,
    reaction: int | None,
) -> ReviewItem:
    return ReviewItem(
        id=review.id,
        author_nickname=nickname,
        body=review.body,
        likes=likes,
        dislikes=dislikes,
        created_at=review.created_at,
        updated_at=review.updated_at,
        mine=viewer is not None and review.user_id == viewer,
        my_reaction=reaction if reaction in (1, -1) else None,  # type: ignore[arg-type]
    )


def list_reviews(
    session: Session, fixture_id: int, sort: ReviewSort, viewer: uuid.UUID | None = None
) -> ReviewList:
    counts, like_count, dislike_count = _counts()
    total = like_count + dislike_count
    query = (
        select(Review, User.nickname, like_count, dislike_count)
        .join(User, User.id == Review.user_id)
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
    reactions: dict[int, int] = {}
    if viewer is not None and rows:
        reactions = {
            review_id: value
            for review_id, value in session.execute(
                select(ReviewReaction.review_id, ReviewReaction.value).where(
                    ReviewReaction.user_id == viewer,
                    ReviewReaction.review_id.in_([row[0].id for row in rows]),
                )
            )
        }
    items = [
        _item(review, nickname, int(up), int(down), viewer, reactions.get(review.id))
        for review, nickname, up, down in rows
    ]
    return ReviewList(summary=ReviewSummary(count=len(items)), items=items)


# --- writing (chat 02) ------------------------------------------------------------------


def clean_body(body: str) -> str:
    """REV-002: not empty, not only spaces (same rule as the DB check), at most 300. Spaces
    around the text are dropped before saving."""
    body = body.strip()
    if not body:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "평가 내용을 입력해 주세요.",
            details={"fields": {"body": "내용을 입력해 주세요."}},
        )
    if len(body) > REVIEW_BODY_MAX:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            f"평가는 최대 {REVIEW_BODY_MAX}자까지 쓸 수 있습니다.",
            details={"fields": {"body": f"최대 {REVIEW_BODY_MAX}자까지 입력할 수 있습니다."}},
        )
    return body


def _open_fixture(session: Session, fixture_id: int) -> Fixture:
    fixture = session.get(Fixture, fixture_id)
    if fixture is None:
        raise ApiError(404, "NOT_FOUND", "경기를 찾을 수 없습니다.")
    if not review_open(fixture):
        raise ApiError(409, "CONFLICT", CLOSED)
    return fixture


def _one(session: Session, review_id: int, viewer: uuid.UUID) -> ReviewItem:
    counts, like_count, dislike_count = _counts()
    review, nickname, up, down = session.execute(
        select(Review, User.nickname, like_count, dislike_count)
        .join(User, User.id == Review.user_id)
        .outerjoin(counts, counts.c.review_id == Review.id)
        .where(Review.id == review_id)
    ).one()
    reaction = session.scalar(
        select(ReviewReaction.value).where(
            ReviewReaction.review_id == review_id, ReviewReaction.user_id == viewer
        )
    )
    return _item(review, nickname, int(up), int(down), viewer, reaction)


def _own(session: Session, review_id: int, user_id: uuid.UUID) -> Review:
    review = session.get(Review, review_id)
    if review is None:
        raise ApiError(404, "NOT_FOUND", REVIEW_NOT_FOUND)
    if review.user_id != user_id:
        raise ApiError(403, "FORBIDDEN", "본인이 작성한 평가만 수정·삭제할 수 있습니다.")
    return review


def review_restriction(user: User, now: datetime) -> datetime | None:
    """The end of the member's review restriction (terms 제9조), or None when free."""
    until = user.review_restricted_until
    return until if until is not None and until > now else None


def _require_unrestricted(session: Session, user_id: uuid.UUID) -> None:
    user = session.get(User, user_id)
    until = review_restriction(user, datetime.now(UTC)) if user else None
    if until is not None:
        kst = until.astimezone(KST).strftime("%Y.%m.%d %H:%M")
        raise ApiError(
            403,
            "REVIEW_RESTRICTED",
            f"운영 정책에 따라 {kst}까지 경기 평가를 작성·수정할 수 없습니다.",
            details={"until": until.isoformat()},
        )


def create_review(session: Session, user_id: uuid.UUID, fixture_id: int, body: str) -> ReviewItem:
    body = clean_body(body)
    _require_unrestricted(session, user_id)
    _open_fixture(session, fixture_id)
    review = Review(user_id=user_id, fixture_id=fixture_id, body=body)
    session.add(review)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(
            409, "REVIEW_EXISTS", "이미 이 경기에 평가를 남겼습니다. 기존 평가를 수정해 주세요."
        ) from None
    return _one(session, review.id, user_id)


def edit_review(session: Session, user_id: uuid.UUID, review_id: int, body: str) -> ReviewItem:
    body = clean_body(body)
    review = _own(session, review_id, user_id)
    _require_unrestricted(session, user_id)
    _open_fixture(session, review.fixture_id)
    if review.body != body:
        review.body = body
        review.updated_at = datetime.now(UTC)
    session.commit()
    return _one(session, review.id, user_id)


def delete_review(session: Session, user_id: uuid.UUID, review_id: int) -> None:
    review = _own(session, review_id, user_id)
    session.delete(review)
    session.commit()


def set_reaction(
    session: Session, user_id: uuid.UUID, review_id: int, value: int | None
) -> ReviewItem:
    """Like (1), dislike (-1) or clear (None). One per member and review (REV-004)."""
    review = session.get(Review, review_id)
    if review is None:
        raise ApiError(404, "NOT_FOUND", REVIEW_NOT_FOUND)
    if review.user_id == user_id:
        raise ApiError(403, "FORBIDDEN", "본인 평가에는 반응할 수 없습니다.")
    _open_fixture(session, review.fixture_id)
    if value is None:
        session.execute(
            delete(ReviewReaction).where(
                ReviewReaction.review_id == review_id, ReviewReaction.user_id == user_id
            )
        )
    else:
        statement = insert(ReviewReaction).values(review_id=review_id, user_id=user_id, value=value)
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["review_id", "user_id"], set_={"value": value}
            )
        )
    session.commit()
    return _one(session, review_id, user_id)


def my_reviews(session: Session, user_id: uuid.UUID) -> list[MyReview]:
    """The member's reviews, newest first, with the match (my page, chat 09)."""
    counts, like_count, dislike_count = _counts()
    rows = session.execute(
        select(Review, like_count, dislike_count, Fixture)
        .join(Fixture, Fixture.id == Review.fixture_id)
        .outerjoin(counts, counts.c.review_id == Review.id)
        .where(Review.user_id == user_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    lookup = team_detail_lookup(session)
    result = []
    for review, up, down, fixture in rows:
        competition = session.get(Competition, fixture.competition_id)
        home = session.get(Team, fixture.home_team_id)
        away = session.get(Team, fixture.away_team_id)
        result.append(
            MyReview(
                id=review.id,
                match=to_summary(fixture, competition, home, away, lookup),
                body=review.body,
                likes=int(up),
                dislikes=int(down),
                created_at=review.created_at,
                edited_at=review.updated_at if review.updated_at > review.created_at else None,
            )
        )
    return result
