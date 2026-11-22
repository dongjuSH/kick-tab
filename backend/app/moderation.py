"""Operator CLI for the terms (articles 8 and 9, posts and use restrictions; no admin screen):

  uv run python -m app.moderation restrict <email> --days 7|30
  uv run python -m app.moderation lift <email>
  uv run python -m app.moderation remove-review <review_id>
  uv run python -m app.moderation close-account <email> --confirm

Each command prints what changed so the operator can send the notice mail from the
contact mailbox (kicktab2026@gmail.com). Nothing is mailed automatically.
"""

import argparse
import sys
from datetime import UTC, datetime

from app.core.kst import KST
from app.db.session import get_sessionmaker
from app.services import moderation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.moderation",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    restrict = commands.add_parser("restrict", help="block writing/editing reviews")
    restrict.add_argument("email")
    restrict.add_argument("--days", type=int, required=True, choices=moderation.RESTRICTION_DAYS)
    lift = commands.add_parser("lift", help="end a review restriction now")
    lift.add_argument("email")
    remove = commands.add_parser("remove-review", help="delete a review")
    remove.add_argument("review_id", type=int)
    close = commands.add_parser("close-account", help="delete the account (as withdrawal)")
    close.add_argument("email")
    close.add_argument("--confirm", action="store_true", help="required: cannot be undone")
    args = parser.parse_args(argv)

    with get_sessionmaker()() as db:
        try:
            if args.command == "restrict":
                until = moderation.restrict_reviews(db, args.email, args.days, datetime.now(UTC))
                print(f"Reviews restricted until {until.astimezone(KST):%Y-%m-%d %H:%M} KST")
            elif args.command == "lift":
                moderation.lift_restriction(db, args.email)
                print("Review restriction lifted")
            elif args.command == "remove-review":
                removed = moderation.remove_review(db, args.review_id)
                print(
                    f"Review {removed.review_id} (match {removed.fixture_id}) deleted; "
                    f"notify {removed.author_email or 'the author (account gone)'}"
                )
            else:
                if not args.confirm:
                    print(
                        "close-account deletes the account for good; add --confirm", file=sys.stderr
                    )
                    return 2
                moderation.close_account(db, args.email)
                print("Account closed")
        except moderation.ModerationError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
