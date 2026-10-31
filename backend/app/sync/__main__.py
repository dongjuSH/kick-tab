"""CLI: uv run python -m app.sync <job> [key=value ...] | --list"""

import argparse
import logging
import sys

from app.sync import jobs  # noqa: F401  (registers feature jobs)
from app.sync.registry import JOBS
from app.sync.runner import run_job

EXIT_CODES = {"succeeded": 0, "failed": 1, "skipped": 3}


def _parse_params(pairs: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise SystemExit(f"Invalid parameter (expected key=value): {pair}")
        params[key] = value
    return params


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.sync", description="Run a sync job")
    parser.add_argument("job", nargs="?", help="registered job name")
    parser.add_argument("params", nargs="*", help="job parameters as key=value")
    parser.add_argument("--list", action="store_true", help="list registered jobs")
    args = parser.parse_args(argv)

    if args.list or not args.job:
        if not JOBS:
            print("No sync jobs registered yet.")
        for spec in sorted(JOBS.values(), key=lambda s: s.name):
            print(f"{spec.name}\t{spec.description}")
        return 0 if args.list else 2
    if args.job not in JOBS:
        print(f"Unknown sync job: {args.job}", file=sys.stderr)
        return 2

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    outcome = run_job(args.job, _parse_params(args.params))
    print(
        f"{outcome.job}: {outcome.status} (run {outcome.run_id}, "
        f"API requests {outcome.api_requests})"
        + (f" - {outcome.error_summary}" if outcome.error_summary else "")
    )
    return EXIT_CODES[outcome.status]


if __name__ == "__main__":
    raise SystemExit(main())
