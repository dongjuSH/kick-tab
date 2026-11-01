import os
import uuid

import pytest

from app.database import CA_CERTIFICATE
from app.db.session import connect_args, sqlalchemy_url
from app.models import Feedback, SyncRun


def test_database_url_switches_to_psycopg_driver():
    assert sqlalchemy_url("postgresql://u:p@db.example:5432/postgres").startswith(
        "postgresql+psycopg://u:p@db.example:5432/"
    )
    assert sqlalchemy_url("postgres://u:p@h/db").startswith("postgresql+psycopg://")


@pytest.mark.parametrize("bad", ["", "mysql://u:p@h/db"])
def test_database_url_must_be_postgresql(bad):
    with pytest.raises(ValueError):
        sqlalchemy_url(bad)


def test_engine_keeps_verified_tls():
    args = connect_args()
    assert args["sslmode"] == "verify-full"
    assert args["sslrootcert"] == str(CA_CERTIFICATE)


def test_models_match_guide_tables():
    assert Feedback.__table__.c.user_id.nullable is True
    assert not Feedback.__table__.c.user_id.foreign_keys  # FK is added by chat 02
    assert Feedback.__table__.c.type.nullable is True
    assert "ip" not in {c.name for c in Feedback.__table__.c}
    assert {c.name for c in SyncRun.__table__.c} == {
        "id", "job", "params", "started_at", "finished_at", "status", "api_requests",
        "error_summary",
    }


@pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)
def test_feedback_constraints_on_dev_database():
    """Writes inside a transaction that is always rolled back."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    from app.db.session import get_engine
    from app.schemas.feedback import FeedbackCreate
    from app.services.feedback import DuplicateFeedbackError, create_feedback

    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            body = f"통합 확인 {uuid.uuid4()}"
            row = create_feedback(session, FeedbackCreate(body=body, type="other"))
            assert row.id is not None and row.user_id is None and row.created_at is not None
            assert row.body_hash is not None and len(row.body_hash) == 64
            with pytest.raises(DuplicateFeedbackError):
                create_feedback(session, FeedbackCreate(body=f"  {body.upper()} ", type="bug"))
            with pytest.raises(IntegrityError):
                with session.begin_nested():
                    session.execute(text("INSERT INTO feedback (body) VALUES ('')"))
            with pytest.raises(IntegrityError):
                with session.begin_nested():
                    session.execute(text("INSERT INTO feedback (body, type) VALUES ('x', 'spam')"))
            rls = connection.execute(
                text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.feedback'::regclass")
            ).scalar()
            assert rls is True
        finally:
            transaction.rollback()


@pytest.mark.skipif(
    os.environ.get("KICKTAB_DB_TESTS") != "1",
    reason="opt-in: set KICKTAB_DB_TESTS=1 to run against the dev database (rolled back)",
)
def test_concurrent_same_body_waits_for_the_first_transaction():
    """A second submission of the same body blocks until the first transaction ends."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    from app.db.session import get_engine
    from app.schemas.feedback import FeedbackCreate
    from app.services.feedback import body_hash, create_feedback, duplicate_lock_key

    body = f"동시 제출 확인 {uuid.uuid4()}"
    key = duplicate_lock_key(body_hash(body))
    engine = get_engine()
    with engine.connect() as first, engine.connect() as second:
        first_tx = first.begin()
        second_tx = second.begin()
        try:
            session = Session(bind=first, join_transaction_mode="create_savepoint")
            create_feedback(session, FeedbackCreate(body=body, type="other"))
            # The first transaction still holds the lock (its row is not committed).
            assert second.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}
            ).scalar() is False
            second.execute(text("SET LOCAL lock_timeout = '300ms'"))
            other = Session(bind=second, join_transaction_mode="create_savepoint")
            with pytest.raises(OperationalError):
                create_feedback(other, FeedbackCreate(body=body, type="bug"))
        finally:
            second_tx.rollback()
            first_tx.rollback()
