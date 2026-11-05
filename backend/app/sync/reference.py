"""Reference sync (daily + manual): competitions, seasons, five-league teams, aliases.

API requests per run: 14 (/leagues per competition) + 8 (/teams per league and UEFA
competition) = 22. UEFA participants tell news classification which competition a club
actually plays this season.
A failed competition or league keeps its previous rows (CMP-004); the run is recorded as
failed with the affected IDs only after the others are saved.
"""

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reference import CompetitionSeason, Team, TeamCompetitionSeason
from app.providers.api_football import (
    ApiFootballBudgetExceeded,
    ApiFootballConfigError,
    ApiFootballError,
    ApiFootballStopped,
)
from app.seed.competitions import COMPETITIONS, LEAGUE_IDS, UEFA_IDS, season_label
from app.services.reference import (
    add_participation,
    apply_alias_seed,
    load_alias_seed,
    managed_seasons,
    upsert_competitions,
    upsert_teams,
)
from app.sync.registry import JobContext, JobPartialFailure, register_job

logger = logging.getLogger(__name__)


def _log_missing_uefa_names(session: Session, season: int) -> None:
    missing = list(session.scalars(
        select(Team.id).join(TeamCompetitionSeason, TeamCompetitionSeason.team_id == Team.id)
        .where(
            TeamCompetitionSeason.season == season,
            TeamCompetitionSeason.competition_id.in_(UEFA_IDS),
            Team.name_ko.is_(None),
        ).distinct().order_by(Team.id)
    ))
    if missing:
        logger.warning("UEFA teams need Korean names (season %d): %s", season, missing)

# Errors after which every further request would fail too.
FATAL = (ApiFootballStopped, ApiFootballBudgetExceeded, ApiFootballConfigError)


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _save_season(
    session: Session, competition_id: int, season: int, league: dict[str, Any] | None
) -> None:
    seasons = (league or {}).get("seasons") or []
    found = next((s for s in seasons if s.get("year") == season), None)
    now = datetime.now(UTC)
    values = {
        "competition_id": competition_id,
        "season": season,
        "label": season_label(season),
        "is_current": season == settings.current_season,
        # The provider answered without this season: structurally no data (V-16).
        "availability": "available" if found else "no_data",
        "start_date": _date(found.get("start")) if found else None,
        "end_date": _date(found.get("end")) if found else None,
        "updated_at": now,
    }
    stmt = insert(CompetitionSeason).values(values)
    update = {k: v for k, v in values.items() if k not in ("competition_id", "season")}
    # A season whose whole list was already loaded never turns into "no data" because one
    # /leagues answer left it out (CMP-004): its stored results stay offered.
    keep = CompetitionSeason.season_fixtures_synced_at.is_not(None) & (
        stmt.excluded.availability == "no_data"
    )
    for column in ("availability", "start_date", "end_date"):
        update[column] = case(
            (keep, getattr(CompetitionSeason, column)), else_=getattr(stmt.excluded, column)
        )
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=[CompetitionSeason.competition_id, CompetitionSeason.season],
            set_=update,
        )
    )


@register_job(
    "reference",
    description="Competitions, managed seasons, league/UEFA team lists and aliases (22 requests)",
    # 04:00 KST daily, before the morning schedule refresh.
    schedule={"trigger": "cron", "hour": 19, "minute": 0},
)
def sync_reference(ctx: JobContext) -> None:
    season = int(ctx.params.get("season", settings.current_season))
    session = ctx.session
    upsert_competitions(session)
    session.commit()

    client = ctx.api_football()
    failed: list[str] = []
    for seed in COMPETITIONS:
        try:
            result = client.get("/leagues", {"id": seed.id})
        except FATAL:
            raise
        except ApiFootballError as exc:
            logger.warning("leagues %s failed: %s", seed.id, type(exc).__name__)
            failed.append(f"leagues:{seed.id}")
            continue
        league = next(iter(result.response or []), None)
        if league is None:
            # An empty answer for a supported league id is not proof of "no season".
            failed.append(f"leagues:{seed.id}:empty")
            continue
        # One /leagues answer lists every season: past seasons are kept current too (CMP-003).
        for managed in managed_seasons():
            _save_season(session, seed.id, managed, league)
        session.commit()

    now = datetime.now(UTC)
    for league_id in (*LEAGUE_IDS, *UEFA_IDS):
        try:
            result = client.get("/teams", {"league": league_id, "season": season})
        except FATAL:
            raise
        except ApiFootballError as exc:
            logger.warning("teams %s failed: %s", league_id, type(exc).__name__)
            failed.append(f"teams:{league_id}")
            continue
        teams = [
            item["team"] for item in result.response or [] if (item.get("team") or {}).get("id")
        ]
        if not teams:
            failed.append(f"teams:{league_id}:empty")
            continue
        upsert_teams(session, teams, now)
        # The provider's list is authoritative for this season: drop stale members.
        session.execute(
            delete(TeamCompetitionSeason).where(
                TeamCompetitionSeason.competition_id == league_id,
                TeamCompetitionSeason.season == season,
                TeamCompetitionSeason.team_id.not_in([t["id"] for t in teams]),
            )
        )
        add_participation(session, ((t["id"], league_id, season) for t in teams))
        session.execute(
            CompetitionSeason.__table__.update()
            .where(
                CompetitionSeason.competition_id == league_id,
                CompetitionSeason.season == season,
            )
            .values(teams_synced_at=now)
        )
        session.commit()

    result = apply_alias_seed(session, load_alias_seed())
    _log_missing_uefa_names(session, season)
    session.commit()
    logger.info(
        "aliases: %d teams named, %d aliases, %d seed teams not collected yet",
        result.teams_named,
        result.aliases,
        len(result.missing_team_ids),
    )
    if failed:
        raise JobPartialFailure(f"Failed: {', '.join(failed)}")


@register_job("team_aliases", description="Reload the team alias seed only (0 requests)")
def sync_team_aliases(ctx: JobContext) -> None:
    result = apply_alias_seed(ctx.session, load_alias_seed())
    _log_missing_uefa_names(ctx.session, settings.current_season)
    ctx.session.commit()
    if result.missing_team_ids:
        logger.info("seed teams not collected yet: %s", result.missing_team_ids)
