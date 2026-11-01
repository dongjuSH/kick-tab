"""Collection job registry. Feature chats add jobs with @register_job (guide §6.5)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.providers.api_football import ApiFootballClient


@dataclass
class JobContext:
    session: Session
    params: Mapping[str, Any]
    # Requests to providers without a tracked client (e.g. NAVER news), added by the job.
    other_api_requests: int = 0
    _clients: list[ApiFootballClient] = field(default_factory=list, init=False)

    def api_football(self, **kwargs: Any) -> ApiFootballClient:
        """Client whose network attempts are counted into sync_runs.api_requests,
        even when the job fails part-way."""
        client = ApiFootballClient(**kwargs)
        self._clients.append(client)
        return client

    @property
    def api_requests(self) -> int:
        return self.other_api_requests + sum(c.request_count for c in self._clients)

    def close(self) -> None:
        for client in self._clients:
            client.close()


JobFunc = Callable[[JobContext], None]


@dataclass(frozen=True)
class JobSpec:
    name: str
    func: JobFunc
    description: str = ""
    # APScheduler trigger kwargs, e.g. {"trigger": "interval", "minutes": 30}.
    # None = manual only (CLI).
    schedule: Mapping[str, Any] | None = None
    default_params: Mapping[str, Any] = field(default_factory=dict)


JOBS: dict[str, JobSpec] = {}


def register_job(
    name: str,
    *,
    description: str = "",
    schedule: Mapping[str, Any] | None = None,
    default_params: Mapping[str, Any] | None = None,
) -> Callable[[JobFunc], JobFunc]:
    """Register an idempotent job function `func(ctx: JobContext) -> None`."""

    def decorator(func: JobFunc) -> JobFunc:
        if name in JOBS:
            raise ValueError(f"Duplicate sync job: {name}")
        JOBS[name] = JobSpec(name, func, description, schedule, dict(default_params or {}))
        return func

    return decorator
