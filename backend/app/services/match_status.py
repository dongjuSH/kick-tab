"""API-Football status.short -> service status (guide §6.4 table, LIVE-001, D-17)."""

from typing import NamedTuple

LIVE_CODES = frozenset({"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "SUSP", "INT"})
_FINISHED = {
    "FT": "normal",
    "AET": "aet",
    "PEN": "pen",
    "AWD": "awarded",
    "WO": "walkover",
}


class MappedStatus(NamedTuple):
    status: str
    finish_type: str | None
    time_confirmed: bool


def map_status(short: str | None) -> MappedStatus:
    """Case-insensitive (real data mixes `Canc` and `CANC`). Unknown codes -> unknown."""
    code = (short or "").strip().upper()
    if code in ("NS", "TBD"):
        return MappedStatus("scheduled", None, code == "NS")
    if code in LIVE_CODES:
        return MappedStatus("live", None, True)
    if code in _FINISHED:
        return MappedStatus("finished", _FINISHED[code], True)
    if code == "PST":
        # The provider keeps the original date while PST; a rescheduled match returns to
        # NS/TBD on the same id with the new date, so a PST kickoff is never the new time.
        return MappedStatus("postponed", None, False)
    if code == "CANC":
        return MappedStatus("cancelled", None, True)
    if code == "ABD":
        return MappedStatus("abandoned", None, True)
    return MappedStatus("unknown", None, True)
