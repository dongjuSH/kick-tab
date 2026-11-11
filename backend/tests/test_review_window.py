"""04 개선: the match review window (REV-001), decided on the server by `review_open`."""

import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.review import REVIEW_BODY_SPACE_CLASS
from app.services.reviews import review_open


def _expand(char_class: str) -> set[str]:
    """Characters of a PostgreSQL ARE bracket body written with \\t-style and \\uXXXX escapes."""
    simple = {"t": "\t", "n": "\n", "v": "\v", "f": "\f", "r": "\r"}
    chars = [
        chr(int(m.group(1), 16)) if m.group(1) else simple.get(m.group(2), m.group(2) or m.group(3))
        for m in re.finditer(r"\\u([0-9a-fA-F]{4})|\\(.)|(.)", char_class)
    ]
    out: set[str] = set()
    i = 0
    while i < len(chars):
        if i + 2 < len(chars) and chars[i + 1] == "-":
            out.update(chr(c) for c in range(ord(chars[i]), ord(chars[i + 2]) + 1))
            i += 3
        else:
            out.add(chars[i])
            i += 1
    return out


def test_blank_body_class_is_exactly_python_whitespace():
    # A body passes the DB check iff body.strip() is not empty (chat 02 validates that way).
    python_spaces = {chr(c) for c in range(sys.maxunicode + 1) if chr(c).isspace()}
    assert _expand(REVIEW_BODY_SPACE_CLASS) == python_spaces
    path = next(Path(__file__).parents[1].glob("migrations/versions/*_0015_text_reviews.py"))
    spec = importlib.util.spec_from_file_location("m0015", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.VISIBLE == f"body ~ '[^{REVIEW_BODY_SPACE_CLASS}]'"


@pytest.mark.parametrize(
    ("status", "finish_type", "code", "expected"),
    [
        ("live", None, "1H", True),
        ("live", None, "HT", True),
        ("live", None, "ET", True),
        ("live", None, "P", True),
        ("live", None, "INT", True),  # a short interruption inside the match
        ("finished", "normal", "FT", True),
        ("finished", "aet", "AET", True),
        ("finished", "pen", "PEN", True),
        # Closed: before kickoff, suspended/stopped/cancelled, rulings (recommended option).
        ("live", None, "SUSP", False),
        ("live", None, "susp", False),
        ("scheduled", None, "NS", False),
        ("postponed", None, "PST", False),
        ("cancelled", None, "CANC", False),
        ("abandoned", None, "ABD", False),
        ("finished", "awarded", "AWD", False),
        ("finished", "walkover", "WO", False),
        ("unknown", None, "XYZ", False),
    ],
)
def test_review_window_by_state(status, finish_type, code, expected):
    match = SimpleNamespace(status=status, finish_type=finish_type, status_short_raw=code)
    assert review_open(match) is expected


def test_review_window_keeps_the_same_match_from_live_to_finish():
    match = SimpleNamespace(status="live", finish_type=None, status_short_raw="2H")
    assert review_open(match)
    match.status_short_raw = "SUSP"  # suspended: hidden, not deleted (P-07)
    assert not review_open(match)
    match.status_short_raw = "2H"  # resumed: shown again
    assert review_open(match)
    match.status, match.finish_type, match.status_short_raw = "finished", "normal", "FT"
    assert review_open(match)
