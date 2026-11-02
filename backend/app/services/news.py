"""Main news read model (NEWS-001·002): newest first, badge filter, cursor paging."""

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.models.news import NewsArticle
from app.models.sync_run import SyncRun
from app.schemas.schedule import NewsItem


class InvalidCursor(ValueError):
    pass


def encode_cursor(published_at: datetime, article_id: int) -> str:
    raw = f"{published_at.astimezone(UTC).isoformat()}|{article_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        stamp, article_id = raw.split("|")
        return datetime.fromisoformat(stamp), int(article_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursor(str(type(exc).__name__)) from None


@dataclass(frozen=True)
class NewsCollection:
    updated_at: datetime | None
    stale: bool
    empty_store: bool


def collection_state(session: Session, now: datetime) -> NewsCollection:
    last_ok = session.scalar(
        select(SyncRun.finished_at)
        .where(SyncRun.job == "news", SyncRun.status == "succeeded")
        .order_by(SyncRun.finished_at.desc())
        .limit(1)
    )
    last_status = session.scalar(
        select(SyncRun.status)
        .where(SyncRun.job == "news", SyncRun.status.in_(("succeeded", "failed")))
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )
    empty = (
        session.scalar(select(NewsArticle.id).where(NewsArticle.expires_at > now).limit(1)) is None
    )
    return NewsCollection(last_ok, last_status == "failed", empty)


def list_news(
    session: Session, now: datetime, *, badge: str | None, size: int, cursor: str | None
) -> tuple[list[NewsItem], str | None]:
    conditions = [NewsArticle.expires_at > now, NewsArticle.badge.is_not(None)]
    if badge:
        conditions.append(NewsArticle.badge == badge)
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
    return items, next_cursor
