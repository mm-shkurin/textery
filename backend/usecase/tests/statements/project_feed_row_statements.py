"""Test DSL for scenario 1.1 -- the feed row carries the contract's full shape.

Given the feed projection holds one fully populated row of the caller's
When they request their projects
Then every field the contract declares reaches the caller
And the usecase neither drops, defaults nor derives any of them.

Pass-through is the whole claim here: `ProjectItem`'s values are the db adapter's
to produce (`red-adapter db`, next pair). What this pins is that `ListProjects`
hands the port's row on untouched.
"""

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fake.auth.fake_clock import FakeClock
from fake.project.fake_project_feed_repository import (
    FakeProjectFeedRepository,
    FakeSearchSlots,
)
from project.list_projects import ListProjects
from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest

_FIXED_NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)

# The contract's row (api-specs/projects_list.yaml #/components/schemas/ProjectItem),
# stated once as literals so the seeding and the assertion cannot drift apart, and
# so a usecase that defaulted a field is caught by value rather than by presence.
#
# Every value is distinct from every other: `created_at` and `updated_at` differ, so
# a row built by copying one into the other goes red rather than passing.
#
# `retryable` is deliberately True on a `document` row -- a combination the db arm
# will never emit, precisely because a usecase that hardcoded the contract's
# document default (False) instead of forwarding the port's value would otherwise
# pass. The usecase does not know kinds; forwarding is its entire job.
_EXPECTED_ROW = {
    "kind": "document",
    "id": UUID("11111111-2222-3333-4444-555555555555"),
    "title": "Байкал: доклад",
    "preview": "Байкал — самое глубокое озеро планеты.",
    "document_type": "доклад",
    "status": "draft",
    "retryable": True,
    "created_at": datetime(2026, 7, 30, 9, 15, tzinfo=UTC),
    "updated_at": datetime(2026, 7, 31, 18, 40, tzinfo=UTC),
}


class ProjectFeedRowStatements:
    def __init__(self) -> None:
        self._repository = FakeProjectFeedRepository()
        self._usecase = ListProjects(
            project_feed_repository=self._repository,
            search_slots=FakeSearchSlots(),
            clock=FakeClock(_FIXED_NOW),
        )
        self._caller_id = uuid4()

    def given_the_feed_holds_one_fully_populated_row_of_the_callers(self) -> None:
        self._repository.seed(self._caller_id, ProjectItem(**_EXPECTED_ROW))

    async def when_the_caller_requests_their_projects(self) -> ProjectPage:
        return await self._usecase.execute(
            owner_id=self._caller_id, request=ProjectPageRequest()
        )

    def assert_the_row_reaches_the_caller_unchanged(self, page: ProjectPage) -> None:
        # Guard the guard: the field comparison below reads `page.items[0]`, so an
        # empty page must fail as an empty page rather than as an IndexError whose
        # message says nothing about the shape.
        assert len(page.items) == 1, "the caller's single seeded row must be served"
        # `asdict` compares the row's whole field set in one comparison: a dropped
        # field, an added one and a substituted value each surface by name. A
        # per-field sweep would silently pass over a tenth field the contract does
        # not declare, and this VO is the client's row -- extra fields are contract
        # drift, not harmless.
        assert asdict(page.items[0]) == _EXPECTED_ROW, (
            "every contract field must reach the caller exactly as the port served it"
        )
