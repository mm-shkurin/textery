import logging
from dataclasses import dataclass

from health.health_probe import HealthProbe

logger = logging.getLogger(__name__)

DATABASE_DEPENDENCY = "database"


@dataclass(frozen=True)
class HealthReport:
    """Whether the service can actually serve, and which dependency said no.

    `is_healthy` is what the orchestrator reads. `failed_dependencies` exists for
    the human who then has to find out why, and is empty on the happy path.
    """

    is_healthy: bool
    failed_dependencies: tuple[str, ...]

    @staticmethod
    def healthy() -> "HealthReport":
        return HealthReport(is_healthy=True, failed_dependencies=())


class CheckHealth:
    """Report whether this instance can serve requests, not merely whether it runs.

    The distinction is the whole point. Before this, the container probe in
    `infra/docker/backend.Dockerfile` requested `/openapi.json` -- a schema FastAPI
    renders from objects already in memory. It answers 200 with the database
    unreachable, so a container that had lost its connection pool looked identical
    to a working one and was never restarted.

    The database is the only dependency checked. The generation provider is
    excluded on purpose: a GigaChat outage degrades one endpoint, and reporting
    the instance unhealthy for it would have the orchestrator recycle containers
    that are still serving auth, history and the editor perfectly well.
    """

    def __init__(self, database_probe: HealthProbe) -> None:
        self.database_probe = database_probe

    async def execute(self) -> HealthReport:
        try:
            await self.database_probe.ping()
        except Exception as error:
            # Broad, and it has to be: the probe crosses a driver boundary that can
            # fail as OSError, asyncpg's own errors, or a timeout, and a probe that
            # only survives the exceptions someone anticipated reports healthy on
            # the ones they did not. Logged with the traceback, since the response
            # body deliberately does not carry it.
            logger.warning("health probe failed for %s: %r", DATABASE_DEPENDENCY, error)
            return HealthReport(is_healthy=False, failed_dependencies=(DATABASE_DEPENDENCY,))
        return HealthReport.healthy()
