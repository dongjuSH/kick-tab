"""Run a read-only connection check: python -m app.check_database."""

import psycopg

from app.database import get_connection


def main() -> int:
    try:
        with get_connection() as connection:
            connection.read_only = True
            if connection.execute("SELECT 1").fetchone() != (1,):
                print("Database check failed: unexpected query result")
                return 1
            encrypted = connection.execute(
                "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
            ).fetchone()
            if encrypted != (True,):
                print("Database check failed: encrypted connection not confirmed")
                return 1
    except (psycopg.Error, ValueError):
        # Driver errors can include connection details. Keep credentials out of output.
        print("Database check failed: verify DATABASE_URL, network and CA certificate")
        return 1
    print("Database authentication, SELECT 1 and verified TLS: PASS (read-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
