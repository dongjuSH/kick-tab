"""Import point for job modules so the CLI and scheduler see every @register_job."""

from app.sync import fixtures, news, reference, standings, team_detail, top5  # noqa: F401
