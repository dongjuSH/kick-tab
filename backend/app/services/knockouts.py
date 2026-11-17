"""UEFA knockout ties from stored fixtures (06 개선, LEAG-002 rule 7·8).

Ties are built only from fixtures already collected (`fixtures`, `fixtures_season`); reading
a stage never asks the provider. A tie is the pair of teams of one round: two legs from the
play-offs (Round of 32) to the semi-finals, one match in the final. The winner is the team
with more goals over both legs (extra time included in the provider's goals), and on equal
goals the penalty shoot-out of the deciding match (UEFA has no away-goals rule).

Qualifying rounds ("Play-offs", "Playoff round") are not knockout stages here (rule 8).

When a round has fewer stored ties than it should, one missing tie can still be placed:
the teams of the previous round that no stored tie of this round contains come from the
previous-round ties not used yet. If exactly one tie is missing, its two places are those
ties' winners — or "A–B전 승자" while a tie is not decided, and "상대 미정" when only one such
tie exists. The final is always the two semi-finals. Pairings of later rounds that are not
in stored fixtures (UEFA draws) are never guessed: those ties stay "예정 · 대진 미정".
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.models.fixture import Fixture
from app.models.reference import Team

Stage = Literal["playoff", "r16", "qf", "sf", "final"]
STAGES: tuple[Stage, ...] = ("playoff", "r16", "qf", "sf", "final")
# Provider round names (2025-26 UCL·UEL·UECL) and the number of ties of each stage.
ROUNDS: dict[Stage, str] = {
    "playoff": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarter-finals",
    "sf": "Semi-finals",
    "final": "Final",
}
TIES: dict[Stage, int] = {"playoff": 8, "r16": 8, "qf": 4, "sf": 2, "final": 1}

TieState = Literal["finished", "live", "scheduled", "undecided"]


@dataclass
class Leg:
    fixture: Fixture
    home: Team
    away: Team


@dataclass
class Slot:
    """One side of a tie: a known team, or the winner of an undecided previous tie."""

    team: Team | None = None
    winner_of: "Tie | None" = None


@dataclass
class Tie:
    legs_needed: int
    home: Slot = field(default_factory=Slot)
    away: Slot = field(default_factory=Slot)
    legs: list[Leg] = field(default_factory=list)
    aggregate_home: int | None = None
    aggregate_away: int | None = None
    penalty_home: int | None = None
    penalty_away: int | None = None
    winner: Team | None = None

    @property
    def state(self) -> TieState:
        if self.winner is not None:
            return "finished"
        if any(leg.fixture.status == "live" for leg in self.legs):
            return "live"
        if self.home.team is None and self.away.team is None and self.home.winner_of is None \
                and self.away.winner_of is None:
            return "undecided"
        return "scheduled"

    def team_ids(self) -> set[int]:
        return {s.team.id for s in (self.home, self.away) if s.team is not None}


def _goals(leg: Leg, team_id: int) -> int | None:
    f = leg.fixture
    return f.goals_home if leg.home.id == team_id else f.goals_away


def _decide(tie: Tie) -> None:
    """Aggregate and winner once every leg is finished; nothing is decided before."""
    first, second = tie.home.team, tie.away.team
    if first is None or second is None or len(tie.legs) < tie.legs_needed:
        return
    if any(leg.fixture.status != "finished" for leg in tie.legs):
        return
    goals_first = [_goals(leg, first.id) for leg in tie.legs]
    goals_second = [_goals(leg, second.id) for leg in tie.legs]
    if None in goals_first or None in goals_second:
        return
    tie.aggregate_home, tie.aggregate_away = sum(goals_first), sum(goals_second)  # type: ignore[arg-type]
    if tie.aggregate_home != tie.aggregate_away:
        tie.winner = first if tie.aggregate_home > tie.aggregate_away else second
        return
    last = tie.legs[-1]
    penalty = ((last.fixture.score or {}).get("penalty") or {})
    home_pk, away_pk = penalty.get("home"), penalty.get("away")
    if home_pk is None or away_pk is None or home_pk == away_pk:
        return
    first_pk, second_pk = (home_pk, away_pk) if last.home.id == first.id else (away_pk, home_pk)
    tie.penalty_home, tie.penalty_away = first_pk, second_pk
    tie.winner = first if first_pk > second_pk else second


def _stage_ties(session: Session, league: int, season: int, stage: Stage) -> list[Tie]:
    home, away = aliased(Team), aliased(Team)
    rows = session.execute(
        select(Fixture, home, away)
        .join(home, home.id == Fixture.home_team_id)
        .join(away, away.id == Fixture.away_team_id)
        .where(
            Fixture.competition_id == league,
            Fixture.season == season,
            Fixture.round == ROUNDS[stage],
            Fixture.status != "cancelled",
        )
        .order_by(Fixture.kickoff_at, Fixture.id)
    ).all()
    by_pair: dict[frozenset[int], list[Leg]] = defaultdict(list)
    for fixture, h, a in rows:
        by_pair[frozenset((h.id, a.id))].append(Leg(fixture, h, a))
    ties = []
    for legs in by_pair.values():
        # The first leg's home team is written first (Figma 450:6662).
        tie = Tie(legs_needed=1 if stage == "final" else 2, legs=legs)
        tie.home, tie.away = Slot(team=legs[0].home), Slot(team=legs[0].away)
        _decide(tie)
        ties.append(tie)
    return ties


def _slot_from(feeder: Tie) -> Slot:
    return Slot(team=feeder.winner) if feeder.winner is not None else Slot(winner_of=feeder)


def build_stage(session: Session, league: int, season: int, stage: Stage) -> list[Tie]:
    """Every tie of the stage in kick-off order, completed to the stage's size with the one
    tie the previous round fixes (see the module notes) and "대진 미정" placeholders."""
    ties = _stage_ties(session, league, season, stage)
    expected = TIES[stage]
    missing = expected - len(ties)
    index = STAGES.index(stage)
    if missing == 1 and index > 0:
        previous = _stage_ties(session, league, season, STAGES[index - 1])
        placed = set().union(*(t.team_ids() for t in ties)) if ties else set()
        unused = [p for p in previous if not (p.team_ids() & placed)]
        if len(unused) in (1, 2):
            # Two unused feeders fix both places; one alone (the other not stored) fixes one
            # place and leaves "상대 미정".
            derived = Tie(legs_needed=1 if stage == "final" else 2)
            derived.home = _slot_from(unused[0])
            if len(unused) == 2:
                derived.away = _slot_from(unused[1])
            ties.append(derived)
            missing = 0
    ties.extend(Tie(legs_needed=1 if stage == "final" else 2) for _ in range(max(missing, 0)))
    return ties
