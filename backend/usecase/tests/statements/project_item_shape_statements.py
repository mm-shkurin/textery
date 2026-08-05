"""Structural assertions over the feed row's shape (Scenario 1.1).

The subject here is a *declaration*, not a value, so these methods reflect over
the dataclass rather than driving a usecase. The row's values are pinned by
`ProjectFeedRowStatements`; what cannot be pinned by any value assertion is the
absence of defaults -- a defaulted field still compares equal once something
supplies it, so a green value test says nothing about the call sites that omit it.

Why that matters concretely: while `ProjectItem` carried `id` alone, the storage
adapter's `ProjectItem(id=row_id)` was legal and emitted hollow rows with the whole
suite green. Restoring a default on any field restores exactly that hole.
"""

import dataclasses

from project.project_item import ProjectItem

# Literal, and in declaration order -- not read back off the dataclass, which would
# make the assertion self-referential and pass through any rename.
EXPECTED_FIELD_NAMES = [
    "kind",
    "id",
    "title",
    "preview",
    "document_type",
    "status",
    "retryable",
    "created_at",
    "updated_at",
]


def _defaulted_fields() -> dict[str, object]:
    """Every ProjectItem field that would be omittable at a call site, by name.

    A dataclass expresses "has a default" two ways -- `default` and
    `default_factory` -- and either one makes the field omittable, so both are
    checked and whichever is present is what gets reported.
    """
    return {
        field.name: (
            field.default if field.default is not dataclasses.MISSING else field.default_factory
        )
        for field in dataclasses.fields(ProjectItem)
        if field.default is not dataclasses.MISSING
        or field.default_factory is not dataclasses.MISSING
    }


class ProjectItemShapeStatements:
    def assert_the_row_declares_exactly_the_contract_fields(self) -> None:
        actual = [field.name for field in dataclasses.fields(ProjectItem)]

        assert actual == EXPECTED_FIELD_NAMES, (
            f"ProjectItem must declare exactly these fields, in this order: "
            f"{EXPECTED_FIELD_NAMES}. Got: {actual}. A missing field is a contract "
            "field the client cannot be served; an extra one is contract drift, "
            "since this VO IS the client's row."
        )

    def assert_no_field_carries_a_default(self) -> None:
        defaulted = _defaulted_fields()

        assert defaulted == {}, (
            f"No ProjectItem field may carry a default or default_factory -- got "
            f"{defaulted}. A default makes an incomplete row constructible, so a "
            "call site that projects nothing (the storage adapter's former "
            "`ProjectItem(id=row_id)`) compiles, runs, and serves a hollow row "
            "while every value assertion elsewhere stays green."
        )
