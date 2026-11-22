"""Retention checks: shared changes roll back; committed races use disposable schemas."""

import os
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: KICKTAB_DB_TESTS=1 (shared changes rolled back, race schemas dropped)",
)


def test_only_rows_past_their_retention_are_deleted():
    from app.db.session import get_engine
    from app.models.feedback import Feedback
    from app.models.user import EmailVerification, RefreshToken, User
    from app.services.retention import purge_expired
    from app.sync import jobs  # noqa: F401  (registers every job)
    from app.sync.registry import JOBS

    assert JOBS["retention"].schedule == {"trigger": "cron", "hour": 18, "minute": 30}
    now = datetime.now(UTC)
    day = timedelta(days=1)
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            tag = uuid.uuid4().hex[:10]
            user = User(email=f"ret-{tag}@example.com", nickname=f"r{tag}", password_hash="x",
                        login_method="email", review_restricted_until=now - day)
            running = User(email=f"run-{tag}@example.com", nickname=f"u{tag}",
                           password_hash="x", login_method="email",
                           review_restricted_until=now + 6 * day)
            session.add_all([user, running])
            session.flush()

            def code(name, sent):
                row = EmailVerification(email=f"{name}-{tag}@example.com", purpose="signup",
                                        code_hash="x", expires_at=sent + timedelta(minutes=10),
                                        last_sent_at=sent)
                session.add(row)
                return row

            def token(expires, revoked=None):
                row = RefreshToken(user_id=user.id, token_hash=uuid.uuid4().hex,
                                   family_id=uuid.uuid4(), expires_at=expires, revoked_at=revoked)
                session.add(row)
                return row

            def note(created):
                row = Feedback(body=f"보관 확인 {tag} {created.isoformat()}", type="other",
                               created_at=created)
                session.add(row)
                return row

            old_code, new_code = code("old", now - 31 * day), code("new", now - 29 * day)
            expired = token(now - 31 * day)
            revoked = token(now + 5 * day, revoked=now - 31 * day)
            recent_revoked = token(now + 5 * day, revoked=now - 2 * day)
            live = token(now + 10 * day)
            old_note, new_note = note(now - 366 * day), note(now - 364 * day)
            session.flush()
            ids = {
                "old_code": old_code.id, "new_code": new_code.id, "expired": expired.id,
                "revoked": revoked.id, "recent_revoked": recent_revoked.id, "live": live.id,
                "old_note": old_note.id, "new_note": new_note.id,
            }

            purged = purge_expired(session, now)
            assert purged.verifications >= 1 and purged.refresh_tokens >= 2
            assert purged.feedback >= 1 and purged.restrictions >= 1

            def exists(model, row_id):
                return session.scalar(select(model.id).where(model.id == row_id)) is not None

            assert not exists(EmailVerification, ids["old_code"])
            assert exists(EmailVerification, ids["new_code"])
            assert not exists(RefreshToken, ids["expired"])
            assert not exists(RefreshToken, ids["revoked"])
            assert exists(RefreshToken, ids["recent_revoked"])
            assert exists(RefreshToken, ids["live"])
            assert not exists(Feedback, ids["old_note"])
            assert exists(Feedback, ids["new_note"])
            session.expire_all()
            assert session.get(User, user.id).review_restricted_until is None
            assert session.get(User, running.id).review_restricted_until is not None
        finally:
            transaction.rollback()


# --- resend vs clean-up race (Codex N3·N7) --------------------------------------------
# These tests commit across connections, so they run in a throwaway schema that copies the
# four tables the clean-up touches (empty). Nothing in the shared tables is read or changed,
# and the schema is dropped at the end.

TABLES = ("users", "email_verifications", "refresh_tokens", "feedback")


@contextmanager
def isolated_schema():
    from app.db.session import get_engine

    engine = get_engine()
    schema = f"kt_race_{uuid.uuid4().hex[:10]}"
    connections = []

    def session() -> Session:
        connection = engine.connect()
        # Track it before changing session settings, including an interrupted commit.
        connections.append(connection)
        connection.execute(text(f"SET search_path TO {schema}"))
        connection.commit()
        return Session(bind=connection, expire_on_commit=False)

    try:
        # Setup also belongs inside the cleanup scope: commit may finish just before an
        # exception or KeyboardInterrupt reaches the caller.
        with engine.connect() as admin:
            admin.execute(text(f"CREATE SCHEMA {schema}"))
            for table in TABLES:
                admin.execute(
                    text(f"CREATE TABLE {schema}.{table} (LIKE public.{table} INCLUDING ALL)")
                )
            admin.commit()
        yield session
    finally:
        # Never hand a connection with this search_path back to the pool: drop it instead.
        for connection in connections:
            connection.invalidate()
            connection.close()
        with engine.connect() as admin:
            admin.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            admin.commit()


@pytest.mark.parametrize("interrupted_commit", [1, 2], ids=["schema", "search_path"])
def test_isolated_schema_cleans_up_an_interrupted_setup(monkeypatch, interrupted_commit):
    from sqlalchemy import event
    from sqlalchemy.engine import Connection

    from app.db.session import get_engine

    engine = get_engine()
    tag = uuid.uuid4()
    schema = f"kt_race_{tag.hex[:10]}"
    real_commit = Connection.commit
    commits = []
    interrupted = []
    invalidated = []

    def interrupt_after_commit(connection):
        real_commit(connection)
        commits.append(1)
        if len(commits) == interrupted_commit:
            interrupted.append(connection)
            raise KeyboardInterrupt("interrupted test setup")

    def record_invalidation(dbapi_connection, connection_record, exception):
        invalidated.append(1)

    event.listen(engine, "invalidate", record_invalidation)
    try:
        with monkeypatch.context() as changes:
            changes.setattr(uuid, "uuid4", lambda: tag)
            changes.setattr(Connection, "commit", interrupt_after_commit)
            with pytest.raises(KeyboardInterrupt, match="interrupted test setup"):
                with isolated_schema() as session_factory, session_factory():
                    pytest.fail("setup must be interrupted")

        with engine.connect() as check:
            assert check.scalar(text("SELECT to_regnamespace(:schema)"),
                                {"schema": schema}) is None
        assert interrupted[0].closed
        if interrupted_commit == 2:
            assert invalidated, "a connection with test search_path must not return to the pool"
    finally:
        event.remove(engine, "invalidate", record_invalidation)
        # Keep this regression test safe even when run against the broken helper.
        for connection in interrupted:
            if not connection.closed:
                connection.invalidate()
                connection.close()
        with engine.connect() as cleanup:
            cleanup.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            cleanup.commit()


class _GateSender:
    """Holds request_code() inside its transaction (row lock taken) until released."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.codes: list[str] = []

    def send_code(self, to, purpose, code):
        self.entered.set()
        assert self.release.wait(timeout=15)
        self.codes.append(code)


def _old_row(session_factory, address, now):
    from app.models.user import EmailVerification

    old = now - timedelta(days=31)
    with session_factory() as session:
        session.add(EmailVerification(email=address, purpose="signup", code_hash="x",
                                      expires_at=old, last_sent_at=old))
        session.commit()


def test_resend_holding_the_row_makes_the_clean_up_wait_and_keep_it():
    from app.models.user import EmailVerification
    from app.services import accounts
    from app.services.retention import purge_expired

    with isolated_schema() as session_factory:
        now = datetime.now(UTC)
        address = "race-a@example.com"
        _old_row(session_factory, address, now)
        sender = _GateSender()
        failures: list[str] = []

        def resend():
            try:
                accounts.request_code(session_factory(), address, "signup", sender, now)
            except Exception as exc:  # noqa: BLE001
                failures.append(type(exc).__name__)

        resend_thread = threading.Thread(target=resend)
        resend_thread.start()
        assert sender.entered.wait(timeout=10)
        purge_thread = threading.Thread(target=lambda: purge_expired(session_factory(), now))
        purge_thread.start()
        purge_thread.join(timeout=1.5)
        assert purge_thread.is_alive(), "clean-up must wait for the resend's row lock"
        sender.release.set()
        resend_thread.join(timeout=15)
        purge_thread.join(timeout=15)
        assert failures == [] and len(sender.codes) == 1
        with session_factory() as check:
            row = check.scalar(
                select(EmailVerification).where(EmailVerification.email == address)
            )
            assert row is not None and row.last_sent_at == now


def test_clean_up_holding_the_delete_makes_the_resend_wait_and_start_fresh():
    from app.models.user import EmailVerification
    from app.services import accounts
    from app.services.retention import purge_expired

    with isolated_schema() as session_factory:
        now = datetime.now(UTC)
        address = "race-b@example.com"
        _old_row(session_factory, address, now)
        deleted = threading.Event()
        release = threading.Event()
        purge_session = session_factory()
        real_commit = purge_session.commit
        commits = []

        def gated_commit():
            commits.append(1)
            if len(commits) == 2:  # the code-row DELETE is done but not committed yet
                deleted.set()
                assert release.wait(timeout=15)
            real_commit()

        purge_session.commit = gated_commit
        purge_thread = threading.Thread(target=lambda: purge_expired(purge_session, now))
        purge_thread.start()
        assert deleted.wait(timeout=10)

        sent: list[str] = []
        failures: list[str] = []

        class Sender:
            def send_code(self, to, purpose, code):
                sent.append(code)

        def resend():
            try:
                accounts.request_code(session_factory(), address, "signup", Sender(), now)
            except Exception as exc:  # noqa: BLE001
                failures.append(type(exc).__name__)

        resend_thread = threading.Thread(target=resend)
        resend_thread.start()
        resend_thread.join(timeout=1.5)
        assert resend_thread.is_alive(), "resend must wait for the clean-up's row lock"
        release.set()
        purge_thread.join(timeout=15)
        resend_thread.join(timeout=15)
        assert failures == [] and len(sent) == 1
        with session_factory() as check:
            row = check.scalar(
                select(EmailVerification).where(EmailVerification.email == address)
            )
            assert row is not None and row.last_sent_at == now
