from datetime import UTC, datetime
from uuid import UUID

from project.project_item import ProjectItem

_DOCUMENT_ROW = ProjectItem(
    kind="document",
    id=UUID("11111111-1111-4111-8111-111111111111"),
    title="Экология города",
    preview="Первый абзац доклада.",
    document_type="доклад",
    status="ready",
    retryable=False,
    created_at=datetime(2026, 3, 14, 9, 26, 53, tzinfo=UTC),
    updated_at=datetime(2026, 3, 15, 18, 4, 7, tzinfo=UTC),
)

# Untitled, and the only row with `retryable=True`. `title` is the one field the
# contract leaves nullable, and at this layer the annotation is enforced: a
# `ProjectItemDto` declaring `title: str` raises on this row instead of passing a
# value-only check, which is what the domain's own `str | None` cannot do.
_GENERATION_ROW = ProjectItem(
    kind="generation",
    id=UUID("22222222-2222-4222-8222-222222222222"),
    title=None,
    preview="",
    document_type="эссе",
    status="failed",
    retryable=True,
    created_at=datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC),
    updated_at=datetime(2026, 2, 1, 0, 0, 31, tzinfo=UTC),
)

# Written out by hand rather than derived from the rows above or from
# `ProjectItemDto`: an expectation built by the serializer under test would make
# both sides of the equality one code path and pin nothing.
_EXPECTED_BODY = {
    "items": [
        {
            "kind": "document",
            "id": "11111111-1111-4111-8111-111111111111",
            "title": "Экология города",
            "preview": "Первый абзац доклада.",
            "document_type": "доклад",
            "status": "ready",
            "retryable": False,
            "created_at": "2026-03-14T09:26:53Z",
            "updated_at": "2026-03-15T18:04:07Z",
        },
        {
            "kind": "generation",
            "id": "22222222-2222-4222-8222-222222222222",
            "title": None,
            "preview": "",
            "document_type": "эссе",
            "status": "failed",
            "retryable": True,
            "created_at": "2026-02-01T00:00:00Z",
            "updated_at": "2026-02-01T00:00:31Z",
        },
    ]
}


class TestListProjectsRowSerialization:
    """Story 12 Scenario 1.1: every `ProjectItem` field reaches the wire.

    Given an authenticated caller whose feed holds a titled document row and an
    untitled, retryable generation row
    When they request /api/v1/projects
    Then each row is serialized with all nine fields
    (`#/components/schemas/ProjectItem` in ProductSpecification/api-specs/projects_list.yaml),
    timestamps as UTC ISO-8601 carrying an explicit offset.

    Asserted as one whole-body equality against a hand-written literal. A dropped
    field, a substituted value, an invented tenth field and a naive timestamp all
    fail it, and the literal is not produced by the serializer under test.

    `page`, `limit` and `total` stay out of the expectation on purpose: `ProjectPage`
    still carries `items` alone, and they arrive with their own step. Because the
    comparison is whole-body, a serializer that back-derived `total` from
    `len(items)` fails here rather than passing unnoticed.
    """

    async def test_should_emit_every_project_item_field_for_each_feed_row(
        self, feed_serving, feed_client
    ):
        usecase = feed_serving(_DOCUMENT_ROW, _GENERATION_ROW)

        async with feed_client(usecase) as client:
            response = await client.get("/api/v1/projects")

        assert response.status_code == 200, f"got {response.status_code}: {response.text}"
        assert response.json() == _EXPECTED_BODY, f"unexpected body {response.json()}"
