from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import CA_CERTIFICATE


def sqlalchemy_url(raw_url: str) -> str:
    """Return DATABASE_URL with the psycopg 3 driver (postgresql+psycopg://)."""
    if not raw_url:
        raise ValueError("DATABASE_URL is not configured")
    url = make_url(raw_url)
    if url.get_backend_name() not in ("postgresql", "postgres"):
        raise ValueError("DATABASE_URL must be a PostgreSQL URL")
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


def connect_args() -> dict[str, object]:
    # Same TLS policy as app.database.get_connection.
    return {
        "connect_timeout": 10,
        "sslmode": "verify-full",
        "sslrootcert": str(CA_CERTIFICATE),
    }


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create the engine lazily so imports and tests never need DATABASE_URL."""
    return create_engine(
        sqlalchemy_url(settings.database_url.get_secret_value()),
        connect_args=connect_args(),
        pool_pre_ping=True,
        # Keep driver errors from echoing parameters (they may contain user input).
        hide_parameters=True,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back on error."""
    session = get_sessionmaker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
