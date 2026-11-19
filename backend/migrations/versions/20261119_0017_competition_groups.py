"""Seven more official competitions (chat 03, 2026-11-19): the domestic super cups and the
UEFA Super Cup join their existing groups; the FIFA Club World Cup needs a new `FIFA` group.
The rows themselves are seeded by the `reference` job (app/seed/competitions.py).

Revision ID: 0017_competition_groups
Revises: 0016_team_player_stats
Create Date: 2026-11-19

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017_competition_groups"
down_revision: str | Sequence[str] | None = "0016_team_player_stats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME = "ck_competitions_group_allowed"
OLD = "group_key IN ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'UEFA')"
NEW = "group_key IN ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'UEFA', 'FIFA')"


def upgrade() -> None:
    op.drop_constraint(op.f(NAME), "competitions", type_="check")
    op.create_check_constraint(op.f(NAME), "competitions", NEW)


def downgrade() -> None:
    # A FIFA row cannot satisfy the old rule. Stored matches of it are never deleted here:
    # they may be referenced elsewhere (TOP 5 selections, reviews), so the downgrade stops
    # and they must be handled first (Codex 1차 I, 2026-11-19). Without matches only the
    # master row (and its season rows, cascading) is removed.
    bind = op.get_bind()
    stored = bind.exec_driver_sql(
        "SELECT count(*) FROM fixtures f JOIN competitions c ON c.id = f.competition_id"
        " WHERE c.group_key = 'FIFA'"
    ).scalar_one()
    if stored:
        raise RuntimeError(
            f"0017 downgrade stopped: {stored} stored FIFA match(es) exist. Remove or move"
            " them (and anything referencing them) before downgrading; nothing was deleted."
        )
    op.execute("DELETE FROM competitions WHERE group_key = 'FIFA'")
    op.drop_constraint(op.f(NAME), "competitions", type_="check")
    op.create_check_constraint(op.f(NAME), "competitions", OLD)
