from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from app.config import BACKEND_DIR, settings

CA_CERTIFICATE = BACKEND_DIR / "certs" / "supabase-ca.crt"


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Open a verified TLS connection; commit on success and roll back on failure."""
    url = settings.database_url.get_secret_value()
    if not url:
        raise ValueError("DATABASE_URL is not configured")
    with psycopg.connect(
        url,
        connect_timeout=10,
        sslmode="verify-full",
        sslrootcert=str(CA_CERTIFICATE),
    ) as connection:
        yield connection
