import pytest
from sqlalchemy.exc import DBAPIError, InterfaceError

from access.health.database_health_probe import DatabaseHealthProbe


class TestDatabaseHealthProbeAgainstARunningDatabase:
    async def test_should_return_without_raising(self, db_session):
        """Exercised against real Postgres, not a stubbed session.

        The claim the probe makes is "the pool handed out a connection and the
        server answered on it", and only a real round-trip can establish that. A
        mocked session would assert that `SELECT 1` was passed to `execute`, which
        is a restatement of the implementation rather than a test of the claim.
        """
        await DatabaseHealthProbe(db_session).ping()


class TestDatabaseHealthProbeAgainstAClosedSession:
    async def test_should_raise_rather_than_report_success(self, db_session):
        """A probe that swallowed the failure would be worse than none at all:
        the endpoint would answer 200 with the database gone, and the orchestrator
        would keep routing traffic to an instance that cannot serve a request.

        The exception type is the driver's, which is exactly why `CheckHealth`
        catches broadly rather than naming types it cannot enumerate.
        """
        await db_session.close()
        await db_session.bind.dispose()

        with pytest.raises((DBAPIError, InterfaceError, OSError)):
            await DatabaseHealthProbe(db_session).ping()
