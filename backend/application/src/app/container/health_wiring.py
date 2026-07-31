from sqlalchemy.ext.asyncio import AsyncSession

from access.health.database_health_probe import DatabaseHealthProbe
from container.runtime import request_scoped
from health.check_health import CheckHealth


@request_scoped
def create_check_health(session: AsyncSession) -> CheckHealth:
    return CheckHealth(database_probe=DatabaseHealthProbe(session))
