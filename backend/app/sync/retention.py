"""Daily personal-data clean-up (no external requests). See app/services/retention.py."""

import logging
from datetime import UTC, datetime

from app.services.retention import purge_expired
from app.sync.registry import JobContext, register_job

logger = logging.getLogger(__name__)


@register_job(
    "retention",
    description="Delete expired codes/sessions (30 d) and feedback (1 y); clear ended restrictions",
    schedule={"trigger": "cron", "hour": 18, "minute": 30},  # 03:30 KST
)
def purge_personal_data(ctx: JobContext) -> None:
    purged = purge_expired(ctx.session, datetime.now(UTC))
    # Counts only: no addresses or contents in the log.
    logger.info(
        "Retention: %d code row(s), %d session row(s), %d feedback row(s) deleted; "
        "%d ended restriction(s) cleared",
        purged.verifications,
        purged.refresh_tokens,
        purged.feedback,
        purged.restrictions,
    )
