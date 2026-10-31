"""Alembic environment. Uses DATABASE_URL and the verified TLS settings of the app."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.config import settings
from app.db.base import Base
from app.db.session import connect_args, sqlalchemy_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (python -m alembic upgrade head --sql)."""
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # The URL is never placed in alembic.ini or printed.
    engine = create_engine(
        sqlalchemy_url(settings.database_url.get_secret_value()),
        connect_args=connect_args(),
        poolclass=pool.NullPool,
        hide_parameters=True,
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
