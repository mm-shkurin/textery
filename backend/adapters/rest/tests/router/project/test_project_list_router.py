from uuid import uuid4

from project.project_page import ProjectPage, ProjectPageRequest
from security.current_owner import UNAUTHORIZED_MESSAGE


class TestListProjects:
    """Story 12 Scenario 1.1: the caller's feed is served at GET /api/v1/projects.

    Given an authenticated caller whose feed holds one row
    When they request /api/v1/projects
    Then the row is served as a JSON envelope, scoped to the id the Bearer
    dependency resolved.

    What this pins, and what it deliberately does not:

    `items` and all nine `ProjectItem` fields are pinned. The eight beyond `id`
    arrived with the row-serialization scenario next door
    (`test_project_list_row_serialization.py`), which is where their *contract*
    values are pinned; the values here are the `feed_row` fixture's deliberately
    implausible fillers, so this test keeps asserting the envelope shape rather
    than restating that scenario. `page`, `limit` and `total` are NOT pinned:
    `ProjectPage` carries `items` alone, and a router that derived `total` from
    `len(items)` would be wrong under the offset paging the read-model decision
    chose. Each arrives with the scenario that first asserts it.

    Both the envelope and the row are asserted as whole dicts, not by
    subscripting `items` and `id`: a serializer that also emitted a field the
    domain never gave it -- a `total` back-derived from `len(items)`, a `kind`
    invented at the rest layer -- must fail here rather than pass an id-only
    read. That makes the deferral above enforced rather than merely stated: the
    scenario that first asserts one of those fields is also the one that adds it
    to these dicts.
    """

    async def test_should_serve_the_callers_feed_as_a_json_envelope_of_items(
        self, mocker, feed_client, feed_row
    ):
        project_id = uuid4()
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=ProjectPage(items=(feed_row(project_id),)))

        async with feed_client(usecase) as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "items": [
                {
                    "kind": "",
                    "id": str(project_id),
                    "title": "",
                    "preview": "",
                    "document_type": "",
                    "status": "",
                    "retryable": False,
                    "created_at": "1970-01-01T00:00:00Z",
                    "updated_at": "1970-01-01T00:00:00Z",
                }
            ]
        }, f"unexpected body {response.json()}"

    async def test_should_scope_the_read_to_the_bearer_resolved_owner(
        self, mocker, feed_client, owner_id
    ):
        """The feed is per-account: owner_id is a predicate, never a parameter.

        Asserted on the call rather than the body, because a route that dropped
        the owner would still answer a well-formed 200 with whatever the port
        handed back -- the isolation claim lives in the argument, not the shape.
        """
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock(return_value=ProjectPage(items=()))

        async with feed_client(usecase) as client:
            await client.get("/api/v1/projects")

        usecase.execute.assert_awaited_once_with(owner_id=owner_id, request=ProjectPageRequest())

    async def test_should_return_401_without_an_authorization_header(
        self, mocker, unauthenticated_feed_client
    ):
        """projects_list.yaml: the request fails closed, never as an empty 200."""
        usecase = mocker.Mock()
        usecase.execute = mocker.AsyncMock()

        async with unauthenticated_feed_client(usecase) as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 401, f"got {response.status_code}: {response.text}"
        assert response.json() == {
            "error_code": "UNAUTHORIZED",
            "message": UNAUTHORIZED_MESSAGE,
        }, f"unexpected body {response.json()}"
        # No feed may be read without a token: the refusal happens before the port.
        usecase.execute.assert_not_awaited()
