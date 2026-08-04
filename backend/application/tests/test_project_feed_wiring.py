from unittest.mock import AsyncMock, MagicMock, patch

from access.project.project_feed_storage import SqlAlchemyProjectFeedRepository
from container.project_wiring import create_list_projects
from project.list_projects import ListProjects


class TestCreateListProjectsWiresARealRepository:
    """`SqlAlchemyProjectFeedRepository` was registered in no container.

    The rest suite proves `GET /api/v1/projects` calls whatever `ListProjects`
    the dependency hands it, and the db suite proves the storage emits an
    owner-scoped SELECT -- but both use doubles at the seam between them, so a
    feed wired to nothing at all still passes every one of them and 500s on its
    first real request. That seam is what this pins: the factory must yield a
    real `ListProjects` holding the real repository, on the session the request
    scope opened.
    """

    async def test_should_wire_a_real_feed_repository_on_the_request_session(self):
        sentinel_session = MagicMock()
        sentinel_session.close = AsyncMock()

        with patch("container.runtime.session_factory", return_value=sentinel_session):
            usecase_generator = create_list_projects()
            usecase = await usecase_generator.__anext__()
            try:
                assert isinstance(usecase, ListProjects), (
                    f"expected create_list_projects to build a real ListProjects, got {usecase!r}"
                )

                repository = usecase._project_feed_repository

                assert isinstance(repository, SqlAlchemyProjectFeedRepository), (
                    "expected a real SqlAlchemyProjectFeedRepository so the feed reads "
                    f"the database rather than a stub, got {repository!r}"
                )
                assert repository._session is sentinel_session, (
                    "expected the feed repository to be backed by the request scope's "
                    f"single session, got a different object {repository._session!r}"
                )
            finally:
                await usecase_generator.aclose()


class TestTheCompositionRootServesTheFeed:
    async def test_should_override_the_feed_provider_with_the_real_factory(self):
        from main import app

        from router.project.project_router import get_list_projects_usecase

        assert app.dependency_overrides.get(get_list_projects_usecase) is create_list_projects, (
            "GET /api/v1/projects resolves get_list_projects_usecase, whose unwired stub "
            "raises NotImplementedError -- without this override every real request 500s"
        )
