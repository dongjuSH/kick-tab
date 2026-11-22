"""Personal-data retention (privacy policy 제3조, user decision 2026-11-22).

Once a day, rows past their retention are deleted for good:
- email_verifications: 30 days after the last code was sent (the resend wait and the daily
  send limit only need minutes to a day);
- refresh_tokens: 30 days after they expired or were revoked (reuse detection only needs
  the family while its tokens could still be presented);
- feedback: 1 year after it was received;
- users.review_restricted_until: cleared once the restriction has ended (terms 제9조).
Live sessions, unexpired codes, newer feedback and running restrictions are never touched.

Each step commits on its own, so the job never holds locks on two kinds of rows at once and
cannot form a cycle with requests that lock the account row first (guide §6.2). A resend
that reads a row the job is deleting waits for the row lock (`request_code`).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, or_, update
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.user import EmailVerification, RefreshToken, User

VERIFICATION_RETENTION = timedelta(days=30)
SESSION_RETENTION = timedelta(days=30)
FEEDBACK_RETENTION = timedelta(days=365)


@dataclass(frozen=True)
class Purged:
    verifications: int
    refresh_tokens: int
    feedback: int
    restrictions: int


def purge_expired(session: Session, now: datetime) -> Purged:
    """Delete or clear rows past their retention. Returns the counts."""

    def step(statement) -> int:
        count = session.execute(statement).rowcount
        session.commit()
        return count

    restrictions = step(
        update(User)
        .where(User.review_restricted_until.is_not(None), User.review_restricted_until <= now)
        .values(review_restricted_until=None)
    )
    verifications = step(
        delete(EmailVerification).where(
            EmailVerification.last_sent_at < now - VERIFICATION_RETENTION
        )
    )
    cutoff = now - SESSION_RETENTION
    refresh_tokens = step(
        delete(RefreshToken).where(
            or_(RefreshToken.expires_at < cutoff, RefreshToken.revoked_at < cutoff)
        )
    )
    feedback = step(delete(Feedback).where(Feedback.created_at < now - FEEDBACK_RETENTION))
    return Purged(verifications, refresh_tokens, feedback, restrictions)
