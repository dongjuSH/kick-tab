"""Head-to-head and recent form (MAT-005, also TOP 5 inputs ③·④).

- Meetings: `/fixtures/headtohead?h2h=A-B&last=10`, friendlies and unfinished matches removed.
  Fewer than 5 official meetings while the answer was full -> one wider request without
  `last` (MAT-005 "범위 확대"). Stored per fixture, refreshed only after the two teams have
  met again in a collected match.
- Form: `/fixtures?team=X&last=10`, same filter and widening (`last=30`). Stored per team,
  refreshed after the team's next collected result, or after FORM_MAX_AGE (matches outside
  the supported competitions are not collected).
Stored values are normalised dicts; failures never replace them (COM-004).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.kst import kst_date
from app.core.locks import single_flight
from app.models.fixture import Fixture
from app.models.match_detail import HeadToHead as HeadToHeadRow
from app.models.match_detail import TeamForm
from app.models.reference import Competition, Team
from app.providers.api_football import ApiFootballClient, ApiFootballError
from app.schemas.match_detail import (
    FormBlock,
    FormMatch,
    HeadToHead,
    MeetingsBlock,
    MeetingSummary,
    PastMeeting,
)

logger = logging.getLogger(__name__)

ClientFactory = Callable[[], ApiFootballClient]

SHOWN = 5
STORED = 10
FIRST_LAST = 10
WIDER_FORM_LAST = 30
FAILURE_COOLDOWN = timedelta(minutes=5)
FORM_MAX_AGE = timedelta(days=7)
# API-Football "Friendlies Clubs" and national "Friendlies"; names are checked as well.
FRIENDLY_LEAGUE_IDS = frozenset({667, 10})
FINISHED_CODES = frozenset({"FT", "AET", "PEN", "AWD", "WO"})


class EvidenceError(Exception):
    """A head-to-head or form lookup failed (raised only for callers that ask for it)."""


def is_official_result(item: dict[str, Any]) -> bool:
    league = item.get("league") or {}
    if league.get("id") in FRIENDLY_LEAGUE_IDS or "friendl" in str(league.get("name", "")).lower():
        return False
    short = str(((item.get("fixture") or {}).get("status") or {}).get("short") or "").upper()
    return short in FINISHED_CODES


def normalize_result(item: dict[str, Any]) -> dict[str, Any] | None:
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    teams = item.get("teams") or {}
    home, away = teams.get("home") or {}, teams.get("away") or {}
    goals = item.get("goals") or {}
    penalty = (item.get("score") or {}).get("penalty") or {}
    if not fixture.get("id") or not home.get("id") or not away.get("id"):
        return None
    if isinstance(fixture.get("timestamp"), int):
        kickoff = datetime.fromtimestamp(fixture["timestamp"], UTC)
    else:
        try:
            kickoff = datetime.fromisoformat(fixture["date"]).astimezone(UTC)
        except (KeyError, TypeError, ValueError):
            return None
    return {
        "fixtureId": fixture["id"],
        "kickoffAt": kickoff.isoformat(),
        "leagueId": league.get("id"),
        "leagueName": league.get("name"),
        "round": league.get("round"),
        "homeId": home["id"],
        "homeName": home.get("name"),
        "awayId": away["id"],
        "awayName": away.get("name"),
        "goalsHome": goals.get("home"),
        "goalsAway": goals.get("away"),
        "penaltyHome": penalty.get("home"),
        "penaltyAway": penalty.get("away"),
        # Provider winner flags (shoot-out winner for PEN): True / False / None = draw.
        "homeWinner": home.get("winner"),
        "awayWinner": away.get("winner"),
        "status": ((fixture.get("status") or {}).get("short") or "").upper(),
    }


def _official(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows = [normalize_result(i) for i in items or [] if is_official_result(i)]
    return sorted((r for r in rows if r), key=lambda r: r["kickoffAt"], reverse=True)


def _fetch(client: ApiFootballClient, endpoint: str, params: dict[str, Any], wider: dict[str, Any]):
    first = client.get(endpoint, {**params, "last": FIRST_LAST, "timezone": "UTC"})
    rows = _official(first.response)
    if len(rows) < SHOWN and (first.results or 0) >= FIRST_LAST:
        # Friendlies or unfinished matches filled the window: look further back once.
        rows = _official(client.get(endpoint, {**params, **wider, "timezone": "UTC"}).response)
    return rows[:STORED]


def fetch_meetings(client: ApiFootballClient, home_id: int, away_id: int) -> list[dict[str, Any]]:
    return _fetch(client, "/fixtures/headtohead", {"h2h": f"{home_id}-{away_id}"}, {})


def fetch_form(client: ApiFootballClient, team_id: int) -> list[dict[str, Any]]:
    return _fetch(client, "/fixtures", {"team": team_id}, {"last": WIDER_FORM_LAST})


def _newer_result_exists(
    session: Session, team_ids: tuple[int, ...], payload: list[dict[str, Any]], exclude: int | None
) -> bool:
    """A collected finished match of these teams that the stored payload does not know."""
    known = {r["fixtureId"] for r in payload}
    since = max((datetime.fromisoformat(r["kickoffAt"]) for r in payload), default=None)
    if len(team_ids) == 2:
        a, b = team_ids
        teams = or_(
            and_(Fixture.home_team_id == a, Fixture.away_team_id == b),
            and_(Fixture.home_team_id == b, Fixture.away_team_id == a),
        )
    else:
        teams = or_(Fixture.home_team_id == team_ids[0], Fixture.away_team_id == team_ids[0])
    query = select(Fixture.id).where(teams, Fixture.status == "finished")
    if since is not None:
        query = query.where(Fixture.kickoff_at > since)
    if exclude is not None:
        query = query.where(Fixture.id != exclude)
    return any(fid not in known for fid in session.scalars(query))


def _cooling(row: Any, now: datetime) -> bool:
    failed_at = row.last_failed_at if row is not None else None
    return bool(failed_at and now - failed_at < FAILURE_COOLDOWN)


def meetings_due(session: Session, fixture: Fixture, row: HeadToHeadRow | None) -> bool:
    if row is None or row.fetched_at is None:
        return True
    pair = (fixture.home_team_id, fixture.away_team_id)
    return _newer_result_exists(session, pair, row.payload or [], fixture.id)


def form_due(session: Session, team_id: int, row: TeamForm | None, now: datetime) -> bool:
    if row is None or row.fetched_at is None or now - row.fetched_at > FORM_MAX_AGE:
        return True
    return _newer_result_exists(session, (team_id,), row.payload or [], None)


def ensure_meetings(
    session: Session,
    fixture: Fixture,
    now: datetime,
    client_factory: ClientFactory,
    *,
    strict: bool = False,
) -> None:
    """Fetch the meetings once if due. `strict` (TOP 5) raises instead of keeping old data
    silently and ignores the request cool-down."""
    row = session.get(HeadToHeadRow, fixture.id)
    if not meetings_due(session, fixture, row) or (not strict and _cooling(row, now)):
        return
    session.commit()
    with single_flight(session, f"kicktab-h2h:{fixture.id}"):
        session.expire_all()
        row = session.get(HeadToHeadRow, fixture.id)
        if not meetings_due(session, fixture, row) or (not strict and _cooling(row, now)):
            return
        row = row or HeadToHeadRow(fixture_id=fixture.id)
        client = client_factory()
        try:
            payload = fetch_meetings(client, fixture.home_team_id, fixture.away_team_id)
        except ApiFootballError as exc:
            logger.warning("Head-to-head for fixture %s failed: %s", fixture.id, type(exc).__name__)
            row.last_failed_at = now
            session.add(row)
            if strict:
                session.commit()
                raise EvidenceError(f"head-to-head {fixture.id}: {type(exc).__name__}") from None
            return
        finally:
            logger.info(
                "Head-to-head for fixture %s: %d request(s)", fixture.id, client.request_count
            )
            client.close()
        row.payload = payload
        row.last_meeting_fixture_id = payload[0]["fixtureId"] if payload else None
        row.fetched_at = now
        row.last_failed_at = None
        session.add(row)


def ensure_form(
    session: Session,
    team_id: int,
    now: datetime,
    client_factory: ClientFactory,
    *,
    strict: bool = False,
) -> None:
    row = session.get(TeamForm, team_id)
    if not form_due(session, team_id, row, now) or (not strict and _cooling(row, now)):
        return
    session.commit()
    with single_flight(session, f"kicktab-form:{team_id}"):
        session.expire_all()
        row = session.get(TeamForm, team_id)
        if not form_due(session, team_id, row, now) or (not strict and _cooling(row, now)):
            return
        row = row or TeamForm(team_id=team_id)
        client = client_factory()
        try:
            payload = fetch_form(client, team_id)
        except ApiFootballError as exc:
            logger.warning("Form for team %s failed: %s", team_id, type(exc).__name__)
            row.last_failed_at = now
            session.add(row)
            if strict:
                session.commit()
                raise EvidenceError(f"form {team_id}: {type(exc).__name__}") from None
            return
        finally:
            logger.info("Form for team %s: %d request(s)", team_id, client.request_count)
            client.close()
        row.payload = payload
        row.fetched_at = now
        row.last_failed_at = None
        session.add(row)


# ---- read side --------------------------------------------------------------------------


def result_for(row: dict[str, Any], team_id: int) -> str:
    """W / D / L for `team_id` from the provider winner flags."""
    home = row["homeId"] == team_id
    winner = row["homeWinner"] if home else row["awayWinner"]
    loser = row["awayWinner"] if home else row["homeWinner"]
    if winner is True:
        return "W"
    if loser is True:
        return "L"
    return "D"


def competition_names(session: Session) -> dict[int, str]:
    return {c.id: c.name_ko or c.short_name for c in session.scalars(select(Competition))}


def team_names(session: Session, payloads: list[list[dict[str, Any]]]) -> dict[int, str]:
    """Korean names of the teams in stored results, where known (provider name otherwise)."""
    ids = {r[k] for payload in payloads for r in payload for k in ("homeId", "awayId")}
    if not ids:
        return {}
    rows = session.execute(select(Team.id, Team.name_ko).where(Team.id.in_(ids)))
    return {team_id: name for team_id, name in rows if name}


def _name(row: dict[str, Any], side: str, teams: dict[int, str]) -> str:
    return teams.get(row[f"{side}Id"]) or row[f"{side}Name"] or "—"


def _competition(row: dict[str, Any], names: dict[int, str]) -> str:
    return names.get(row.get("leagueId")) or row.get("leagueName") or "—"


def recent_form(payload: list[dict[str, Any]], team_id: int, before: datetime | None = None):
    """The last five official results of a team (optionally before a moment)."""
    rows = [
        r
        for r in payload
        if before is None or datetime.fromisoformat(r["kickoffAt"]) < before
    ]
    return rows[:SHOWN]


def _form_block(
    row: TeamForm | None, team_id: int, names: dict[int, str], teams: dict[int, str]
) -> FormBlock:
    if row is None or row.fetched_at is None:
        return FormBlock(status="unavailable" if row is not None else "not_provided", data=None)
    rows = recent_form(row.payload or [], team_id)
    if not rows:
        return FormBlock(status="not_provided", data=None)
    data = []
    for r in rows:
        home = r["homeId"] == team_id
        data.append(
            FormMatch(
                kickoff_date_kst=kst_date(datetime.fromisoformat(r["kickoffAt"])),
                competition=_competition(r, names),
                opponent_name=_name(r, "away" if home else "home", teams),
                venue="home" if home else "away",
                goals_for=r["goalsHome"] if home else r["goalsAway"],
                goals_against=r["goalsAway"] if home else r["goalsHome"],
                result=result_for(r, team_id),
            )
        )
    return FormBlock(status="available", data=data)


def read_head_to_head(session: Session, fixture: Fixture) -> tuple[HeadToHead, datetime | None]:
    names = competition_names(session)
    row = session.get(HeadToHeadRow, fixture.id)
    home_row = session.get(TeamForm, fixture.home_team_id)
    away_row = session.get(TeamForm, fixture.away_team_id)
    teams = team_names(
        session, [(r.payload or []) for r in (row, home_row, away_row) if r is not None]
    )
    if row is None or row.fetched_at is None:
        meetings = MeetingsBlock(
            status="unavailable" if row is not None else "not_provided", data=None, summary=None
        )
    elif not row.payload:
        meetings = MeetingsBlock(status="not_provided", data=None, summary=None)
    else:
        shown = row.payload[:SHOWN]
        summary = {"W": 0, "D": 0, "L": 0}
        data = []
        for r in shown:
            summary[result_for(r, fixture.home_team_id)] += 1
            data.append(
                PastMeeting(
                    kickoff_date_kst=kst_date(datetime.fromisoformat(r["kickoffAt"])),
                    competition=_competition(r, names),
                    home_name=_name(r, "home", teams),
                    away_name=_name(r, "away", teams),
                    home_is_current_home=r["homeId"] == fixture.home_team_id,
                    score_home=r["goalsHome"],
                    score_away=r["goalsAway"],
                    penalty_home=r["penaltyHome"] if r["status"] == "PEN" else None,
                    penalty_away=r["penaltyAway"] if r["status"] == "PEN" else None,
                )
            )
        meetings = MeetingsBlock(
            status="available",
            data=data,
            summary=MeetingSummary(
                home_wins=summary["W"], draws=summary["D"], away_wins=summary["L"]
            ),
        )
    fetched = [r.fetched_at for r in (row, home_row, away_row) if r is not None and r.fetched_at]
    return (
        HeadToHead(
            meetings=meetings,
            home_form=_form_block(home_row, fixture.home_team_id, names, teams),
            away_form=_form_block(away_row, fixture.away_team_id, names, teams),
        ),
        min(fetched) if fetched else None,
    )
