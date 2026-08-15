"""The three row builders the project-feed router tests seed and assert with.

Split from `conftest.py` for file size. They belong together: `contract_row`
builds the domain row, `expected_row` builds the wire form the router must emit
for it, and `feed_row` pairs them -- so a tenth contract field is one edit across
three fixtures that must agree, and keeping them adjacent is what makes the
disagreement visible.
"""

from datetime import UTC, datetime

import pytest

from project.project_item import ProjectItem


@pytest.fixture
def contract_row():
    """Build a contract-legal domain row carrying the given id.

    The `ProjectItem` construction site for every row a test *varies*: the VO
    permits no field to be absent, so a tenth contract field lands here once
    rather than in each test that seeds a row. Callers replace only the fields
    their assertion names; the rest stay at legal constants, so a row that
    tripped a *different* rule cannot make a failure ambiguous.

    Not the only construction site in the directory --
    `test_project_list_row_serialization.py` builds its two rows inline and on
    purpose. That scenario's whole claim is "every field reaches the wire", and
    it earns it by holding a hand-written domain row and its hand-written wire
    form side by side in one file, neither one sourced from here. A tenth field
    must therefore be added there too; that second edit is the price of the
    independence, not an oversight.
    """

    def _make(project_id, **overrides):
        fields = {
            "kind": "document",
            "id": project_id,
            "title": "Экология города",
            "preview": "Первый абзац доклада.",
            "document_type": "доклад",
            "status": "ready",
            "retryable": False,
            "created_at": datetime(2026, 3, 14, 9, 26, 53, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 15, 18, 4, 7, tzinfo=UTC),
        }
        fields.update(overrides)
        return ProjectItem(**fields)

    return _make


@pytest.fixture
def expected_row():
    """The wire form of `contract_row`'s defaults, with the same fields replaced.

    Written out by hand rather than derived from `contract_row` or from
    `ProjectItemDto`: an expectation the serializer under test produced would make
    both sides of the equality one code path and pin nothing. Tests that compare
    whole rows through this builder fail when a green fixes the field it names but
    drops or corrupts one of the other eight.
    """

    def _make(project_id, **overrides):
        fields = {
            "kind": "document",
            "id": str(project_id),
            "title": "Экология города",
            "preview": "Первый абзац доклада.",
            "document_type": "доклад",
            "status": "ready",
            "retryable": False,
            "created_at": "2026-03-14T09:26:53Z",
            "updated_at": "2026-03-15T18:04:07Z",
        }
        fields.update(overrides)
        return fields

    return _make


@pytest.fixture
def feed_row(contract_row):
    """The envelope test's row: legal, but deliberately implausible.

    The free-form fields carry values no assertion reads -- what the serializer
    emits for them is pinned by the row-serialization scenario, not by the
    envelope test. `kind` and `status` are the exception: projects_list.yaml
    declares them as enums, so `""` would be not merely dull but *illegal*, and a
    fixture that cannot occur in production would quietly outlive the day those
    fields grow constrained types. They keep `contract_row`'s legal members.
    """

    def _make(project_id):
        return contract_row(
            project_id,
            title="",
            preview="",
            document_type="",
            created_at=datetime(1970, 1, 1, tzinfo=UTC),
            updated_at=datetime(1970, 1, 1, tzinfo=UTC),
        )

    return _make
