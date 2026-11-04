"""Main news read model (NEWS-001·002): newest first, badge filter, cursor paging."""

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.models.news import NewsArticle
from app.models.sync_run import SyncRun
from app.schemas.schedule import NewsItem

NEWS_LIMIT = 48


class InvalidCursor(ValueError):
    pass


def encode_cursor(published_at: datetime, article_id: int) -> str:
    raw = f"{published_at.astimezone(UTC).isoformat()}|{article_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        stamp, article_id = raw.split("|")
        published = datetime.fromisoformat(stamp)
        if published.tzinfo is None:
            raise ValueError("Missing timezone")
        return published, int(article_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursor(str(type(exc).__name__)) from None


@dataclass(frozen=True)
class NewsCollection:
    updated_at: datetime | None
    stale: bool
    empty_store: bool
    no_new: bool


def collection_state(session: Session, now: datetime) -> NewsCollection:
    last_ok = session.execute(
        select(SyncRun.started_at, SyncRun.finished_at)
        .where(SyncRun.job == "news", SyncRun.status == "succeeded")
        .order_by(SyncRun.finished_at.desc())
        .limit(1)
    ).first()
    last_status = session.scalar(
        select(SyncRun.status)
        .where(SyncRun.job == "news", SyncRun.status.in_(("succeeded", "failed")))
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )
    latest = session.scalar(
        select(func.max(NewsArticle.fetched_at)).where(
            NewsArticle.expires_at > now, NewsArticle.badge.is_not(None)
        )
    )
    return NewsCollection(
        last_ok.finished_at if last_ok else None,
        last_status == "failed",
        latest is None,
        bool(last_ok and latest and last_status == "succeeded" and latest < last_ok.started_at),
    )


def list_news(
    session: Session, now: datetime, *, badge: str | None, size: int, cursor: str | None
) -> tuple[list[NewsItem], str | None, int]:
    visible = (
        select(NewsArticle.id)
        .where(NewsArticle.expires_at > now, NewsArticle.badge.is_not(None))
        .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
        .limit(NEWS_LIMIT)
    )
    conditions = [NewsArticle.id.in_(visible)]
    if badge:
        conditions.append(NewsArticle.badge == badge)
    total = session.scalar(select(func.count()).select_from(NewsArticle).where(*conditions)) or 0
    if cursor:
        published_at, article_id = decode_cursor(cursor)
        conditions.append(
            tuple_(NewsArticle.published_at, NewsArticle.id) < tuple_(published_at, article_id)
        )
    rows = list(
        session.scalars(
            select(NewsArticle)
            .where(*conditions)
            .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
            .limit(size + 1)
        )
    )
    page = rows[:size]
    next_cursor = (
        encode_cursor(page[-1].published_at, page[-1].id) if len(rows) > size and page else None
    )
    items = [
        NewsItem(
            id=a.id,
            badge=a.badge,
            title=a.title,
            description=a.description,
            url=a.url,
            source_domain=a.source_domain,
            published_at=a.published_at,
        )
        for a in page
    ]
    return items, next_cursor, total
