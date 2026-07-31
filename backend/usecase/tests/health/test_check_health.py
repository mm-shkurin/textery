import pytest

from health.check_health import DATABASE_DEPENDENCY, CheckHealth
from statements.health_statements import (
    a_failing_probe,
    a_probe_failing_with,
    a_reachable_probe,
)


class TestCheckHealthOnAReachableDatabase:
    async def test_should_report_healthy(self):
        report = await CheckHealth(database_probe=a_reachable_probe()).execute()

        assert report.is_healthy is True

    async def test_should_name_no_failed_dependency(self):
        report = await CheckHealth(database_probe=a_reachable_probe()).execute()

        assert report.failed_dependencies == ()


class TestCheckHealthOnAnUnreachableDatabase:
    async def test_should_report_unhealthy(self):
        report = await CheckHealth(database_probe=a_failing_probe()).execute()

        assert report.is_healthy is False

    async def test_should_name_the_database_as_the_failed_dependency(self):
        report = await CheckHealth(database_probe=a_failing_probe()).execute()

        assert report.failed_dependencies == (DATABASE_DEPENDENCY,)

    @pytest.mark.parametrize(
        "raised",
        [
            OSError("connection refused"),
            TimeoutError("no answer within the deadline"),
            RuntimeError("the driver raised something nobody anticipated"),
        ],
    )
    async def test_should_survive_any_failure_the_driver_can_raise(self, raised):
        """The probe crosses a driver boundary, so the exception type is not ours.

        Parameterised over three unrelated types on purpose: a check that only
        catches the errors someone thought of reports HEALTHY on the ones they did
        not, and an orchestrator would then keep routing traffic to an instance
        that cannot reach its database -- the exact failure this endpoint exists
        to catch.
        """
        report = await CheckHealth(database_probe=a_probe_failing_with(raised)).execute()

        assert report.is_healthy is False
        assert report.failed_dependencies == (DATABASE_DEPENDENCY,)

    async def test_should_log_the_failure_with_the_driver_error(self, caplog):
        """The response body carries no reason, so the log is the only record.

        Asserted rather than assumed: the endpoint deliberately answers with the
        dependency name and nothing else, which leaves an operator with no way to
        tell a refused connection from a bad password unless this line exists.
        """
        with caplog.at_level("WARNING"):
            await CheckHealth(database_probe=a_probe_failing_with(OSError("refused"))).execute()

        assert "refused" in caplog.text
        assert DATABASE_DEPENDENCY in caplog.text
