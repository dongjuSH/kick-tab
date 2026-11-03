"""Locks that merge concurrent work on the same key (guide §6.5 "동시 요청 합치기")."""

import hashlib
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

_registry_lock = threading.Lock()
_local_locks: dict[str, threading.Lock] = {}


def advisory_key(name: str) -> int:
    """Signed 64-bit PostgreSQL advisory lock key; `name` carries its own namespace."""
    digest = hashlib.sha256(name.encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _local_lock(name: str) -> threading.Lock:
    with _registry_lock:
        return _local_locks.setdefault(name, threading.Lock())


@contextmanager
def single_flight(session: Session, name: str) -> Iterator[None]:
    """Serialise "check, fetch once, store" for one key.

    Requests in this process wait on a thread lock (so they do not each hold a database
    connection), then every process meets on a transaction-scoped advisory lock. The caller
    re-checks the stored state inside the block and commits before leaving it: the second
    request then finds the first one's result instead of calling the provider again.
    """
    with _local_lock(name):
        session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": advisory_key(name)})
        try:
            yield
        except BaseException:
            session.rollback()
            raise
        # Ends the transaction, which releases the advisory lock, even when nothing was written.
        session.commit()
