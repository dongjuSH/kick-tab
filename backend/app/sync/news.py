"""Hourly news sync: NAVER search per league/UEFA query -> classify -> store.

8 search requests per run (one per query, newest 100 each). Stored: provider title,
description, original link and publish time only, until NEWS_RETENTION_HOURS after
publication. The same article from several queries (same normalized URL, or the same
title syndicated under another URL) is stored once.
"""

import hashlib
import logging
import unicodedata
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.news import NewsArticle, NewsArticleTeam
from app.models.reference import TeamAlias, TeamCompetitionSeason
from app.providers.naver_news import NaverNewsClient, NaverNewsError, NaverNewsStopped
from app.services.news_classify import AliasIndex, classify, plain_text
from app.sync.registry import JobContext, JobPartialFailure, register_job

logger = logging.getLogger(__name__)

QUERIES = (
    "프리미어리그",
    "라리가",
    "세리에A",
    "분데스리가",
    "리그앙",
    "챔피언스리그",
    "유로파리그",
    "컨퍼런스리그",
)
_TRACKING = ("utm_", "fbclid", "gclid")


def normalize_url(url: str) -> str | None:
    """http(s) only; lowercase host without www./m., no fragment or tracking params."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username:
        return None
    host = parts.hostname.lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(_TRACKING)]
    )
    return urlunsplit(("https", host, parts.path.rstrip("/") or "/", query, ""))


def url_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode()).hexdigest()


def _published(value: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    return parsed.astimezone(UTC) if parsed and parsed.tzinfo else None


def _alias_index(session: Session) -> AliasIndex:
    rows = session.execute(
        select(TeamAlias.alias, TeamAlias.team_id).where(
            TeamAlias.for_news, TeamAlias.ambiguous.is_(False)
        )
    ).all()
    return AliasIndex.build((alias, team_id) for alias, team_id in rows)


def _participation(session: Session) -> dict[int, frozenset[int]]:
    """Current-season competitions per team (league and UEFA team lists, seen fixtures)."""
    rows = session.execute(
        select(TeamCompetitionSeason.team_id, TeamCompetitionSeason.competition_id).where(
            TeamCompetitionSeason.season == settings.current_season
        )
    ).all()
    grouped: dict[int, set[int]] = {}
    for team_id, competition_id in rows:
        grouped.setdefault(team_id, set()).add(competition_id)
    return {team: frozenset(ids) for team, ids in grouped.items()}


@register_job(
    "news",
    description="NAVER news for the five leagues and UEFA (8 search requests)",
    schedule={"trigger": "cron", "minute": 0},
)
def sync_news(ctx: JobContext) -> None:
    session = ctx.session
    now = datetime.now(UTC)
    retention = timedelta(hours=settings.news_retention_hours)
    index = _alias_index(session)
    participation = _participation(session)
    seen_hashes = set(session.scalars(select(NewsArticle.url_hash)))
    def title_key(title: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", title).casefold().split())

    seen_titles = {title_key(title) for title in session.scalars(select(NewsArticle.title))}
    failed: list[str] = []
    stats = {"fetched": 0, "stored": 0, "duplicate": 0, "excluded": 0, "old": 0}

    client = NaverNewsClient()
    try:
        for query in QUERIES:
            try:
                items = client.search(query)
            except NaverNewsStopped:
                failed.append(query)
                break
            except NaverNewsError as exc:
                logger.warning("news query failed: %s", type(exc).__name__)
                failed.append(query)
                continue
            finally:
                ctx.other_api_requests = client.request_count
            for item in items:
                stats["fetched"] += 1
                link = normalize_url(item.originallink) or normalize_url(item.link)
                title = plain_text(item.title)
                published = _published(item.pub_date)
                if not link or not title or published is None:
                    stats["excluded"] += 1
                    continue
                if published + retention <= now:
                    stats["old"] += 1
                    continue
                digest = url_hash(link)
                if digest in seen_hashes or title_key(title) in seen_titles:
                    stats["duplicate"] += 1
                    continue
                result = classify(item.title, item.description, index, participation)
                if not result.keep:
                    stats["excluded"] += 1
                    continue
                original = item.originallink if normalize_url(item.originallink) else item.link
                article_id = session.scalar(
                    insert(NewsArticle)
                    .values(
                        url_hash=digest,
                        url=original.strip(),
                        source_domain=urlsplit(link).hostname or "",
                        title=title,
                        # A missing description stays empty; nothing is written for it.
                        description=plain_text(item.description) or None,
                        published_at=published,
                        badge=result.badge,
                        fetched_at=now,
                        expires_at=published + retention,
                    )
                    .on_conflict_do_nothing(index_elements=[NewsArticle.url_hash])
                    .returning(NewsArticle.id)
                )
                if article_id is not None and result.team_ids:
                    links = [{"article_id": article_id, "team_id": t} for t in result.team_ids]
                    session.execute(
                        insert(NewsArticleTeam).values(links).on_conflict_do_nothing()
                    )
                seen_hashes.add(digest)
                seen_titles.add(title_key(title))
                stats["stored"] += 1
    finally:
        client.close()

    if failed:
        session.rollback()
        raise JobPartialFailure(f"Failed queries: {len(failed)} of {len(QUERIES)}")

    # Apply the tightened classification to already-stored headlines, without invalidating
    # their stable links or changing the configured metadata retention window.
    for article in session.scalars(
        select(NewsArticle).where(NewsArticle.expires_at > now, NewsArticle.fetched_at < now)
    ):
        classification = classify(article.title, article.description or "", index, participation)
        badge = classification.badge if classification.keep else None
        article.badge = badge
        current_links = set(session.scalars(
            select(NewsArticleTeam.team_id).where(NewsArticleTeam.article_id == article.id)
        ))
        wanted = set(classification.team_ids) if classification.keep else set()
        if current_links - wanted:
            session.execute(delete(NewsArticleTeam).where(
                NewsArticleTeam.article_id == article.id,
                NewsArticleTeam.team_id.in_(current_links - wanted),
            ))
        if wanted - current_links:
            session.execute(insert(NewsArticleTeam).values([
                {"article_id": article.id, "team_id": team_id} for team_id in wanted - current_links
            ]).on_conflict_do_nothing())

    removed = session.execute(delete(NewsArticle).where(NewsArticle.expires_at <= now)).rowcount
    session.commit()
    logger.info("news: %s, expired removed %s", stats, removed)
