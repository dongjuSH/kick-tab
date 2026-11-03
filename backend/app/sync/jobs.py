"""Import point for job modules so the CLI and scheduler see every @register_job."""

from app.sync import fixtures, news, reference, top5  # noqa: F401
