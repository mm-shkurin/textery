import socket

import pytest
from sqlalchemy.exc import DBAPIError, InterfaceError

from access.health.database_health_probe import DatabaseHealthProbe
from session import create_engine, create_session_factory


def _address_nothing_listens_on() -> tuple[str, int]:
    """A loopback port the OS has just confirmed is free, released before returning.

    Bound with port 0 rather than hardcoded: any fixed number is a number some
    other service on the runner may hold, and a test that connects to a stranger
    instead of to nothing is a test whose failure means something else entirely.
    Connecting here refuses immediately -- no timeout, so the case costs
    milliseconds rather than the driver's connect deadline.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()


class TestDatabaseHealthProbeAgainstARunningDatabase:
    async def test_should_return_without_raising(self, db_session):
        """Exercised against real Postgres, not a stubbed session.

        The claim the probe makes is "the pool handed out a connection and the
        server answered on it", and only a real round-trip can establish that. A
        mocked session would assert that `SELECT 1` was passed to `execute`, which
        is a restatement of the implementation rather than a test of the claim.
        """
        await DatabaseHealthProbe(db_session).ping()


class TestDatabaseHealthProbeAgainstAnUnreachableDatabase:
    async def test_should_raise_rather_than_report_success(self, monkeypatch):
        """A probe that swallowed the failure would be worse than none at all:
        the endpoint would answer 200 with the database gone, and the orchestrator
        would keep routing traffic to an instance that cannot serve a request.

        The exception type is the driver's, which is exactly why `CheckHealth`
        catches broadly rather than naming types it cannot enumerate.

        The database is made unreachable by ADDRESS, not by disposing the pool of
        a live one. That was the previous shape of this test and it asserted the
        opposite of what it claimed: `AsyncEngine.dispose()` discards the current
        pool and leaves the engine usable, so the next statement transparently
        opens a fresh connection. Against the running Postgres that CI provides,
        `SELECT 1` therefore succeeded and the case failed with DID NOT RAISE --
        green only on a machine where the database was already gone, red whenever
        the thing it was testing was actually available.

        The engine is the adapter's own `create_engine()`, pointed at a dead
        address through the environment variable it reads. Building a bare
        `create_async_engine` here would skip `pool_pre_ping`, which is the
        setting that decides whether an unreachable server surfaces at checkout or
        at execute -- the exact behaviour under test.
        """
        host, port = _address_nothing_listens_on()
        monkeypatch.setenv("DATABASE_URL", f"postgresql://textery:change-me@{host}:{port}/textery")

        engine = create_engine()
        try:
            async with create_session_factory(engine)() as session:
                with pytest.raises((DBAPIError, InterfaceError, OSError)):
                    await DatabaseHealthProbe(session).ping()
        finally:
            await engine.dispose()
