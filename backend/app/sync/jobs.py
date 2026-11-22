"""Import point for job modules so the CLI and scheduler see every @register_job."""

from app.sync import (  # noqa: F401
    fixtures,
    news,
    reference,
    retention,
    standings,
    team_detail,
    top5,
)
