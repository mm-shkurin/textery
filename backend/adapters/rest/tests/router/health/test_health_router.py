from health.check_health import HealthReport
from router.health.health_router import HEALTHY_STATUS, UNHEALTHY_STATUS


def _usecase_reporting(mocker, report):
    usecase = mocker.Mock()
    usecase.execute = mocker.AsyncMock(return_value=report)
    return usecase


class TestHealthRouteWhenEveryDependencyAnswers:
    async def test_should_answer_200(self, mocker, create_health_client):
        usecase = _usecase_reporting(mocker, HealthReport.healthy())

        async with create_health_client(usecase) as client:
            response = await client.get("/health")

        assert response.status_code == 200

    async def test_should_report_the_ok_status_and_no_failures(self, mocker, create_health_client):
        usecase = _usecase_reporting(mocker, HealthReport.healthy())

        async with create_health_client(usecase) as client:
            response = await client.get("/health")

        assert response.json() == {"status": HEALTHY_STATUS, "failed_dependencies": []}

    async def test_should_not_require_a_token(self, mocker, create_health_client):
        """The caller is the container runtime, which holds no credentials.

        Worth pinning: this router is mounted on the same app as everything else,
        and adding the Bearer dependency to it would make every probe fail closed
        and the orchestrator restart healthy containers in a loop.
        """
        usecase = _usecase_reporting(mocker, HealthReport.healthy())

        async with create_health_client(usecase) as client:
            response = await client.get("/health")

        assert response.status_code == 200


class TestHealthRouteWhenTheDatabaseIsUnreachable:
    async def test_should_answer_503_not_200(self, mocker, create_health_client):
        """The status code is the entire signal an orchestrator reads.

        A body saying "unavailable" under a 200 is a healthy container to every
        probe implementation that ships, so this assertion is the endpoint's
        reason to exist.
        """
        usecase = _usecase_reporting(
            mocker, HealthReport(is_healthy=False, failed_dependencies=("database",))
        )

        async with create_health_client(usecase) as client:
            response = await client.get("/health")

        assert response.status_code == 503

    async def test_should_name_the_failed_dependency(self, mocker, create_health_client):
        usecase = _usecase_reporting(
            mocker, HealthReport(is_healthy=False, failed_dependencies=("database",))
        )

        async with create_health_client(usecase) as client:
            response = await client.get("/health")

        assert response.json() == {
            "status": UNHEALTHY_STATUS,
            "failed_dependencies": ["database"],
        }

    async def test_should_not_leak_the_underlying_reason(self, mocker, create_health_client):
        """Unauthenticated endpoint, so the body follows the same rule as the
        error handlers: name what failed, never why. A driver error can carry a
        host, a port, or a role name.
        """
        usecase = _usecase_reporting(
            mocker, HealthReport(is_healthy=False, failed_dependencies=("database",))
        )

        async with create_health_client(usecase) as client:
            response = await client.get("/health")

        assert set(response.json()) == {"status", "failed_dependencies"}
