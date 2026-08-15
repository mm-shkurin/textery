from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ValidationInfo, field_validator

from project.project_item import ProjectItem
from project.project_page import ProjectPage


class ProjectKind(StrEnum):
    """The source table a row was read from -- never a status.

    Constrained rather than `str` because projects_list.yaml declares it an enum
    (#/components/schemas/ProjectItem). There is no fail-closed member: `kind` is
    the adapter's own discriminator over two hard-coded UNION arms, not a stored
    value a future migration can widen, so an unrecognised one is a bug in this
    process rather than data to be tolerated.
    """

    DOCUMENT = "document"
    GENERATION = "generation"


class ProjectStatus(StrEnum):
    """The contract's eight status values, `unknown` among them.

    `unknown` is a *member*, not an absence: the contract requires the field to be
    present on the fail-closed branch, and a schema that let it be omitted would
    satisfy a looser reading while doing what the rule forbids.
    """

    DRAFT = "draft"
    READY = "ready"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


def _to_status(value: object) -> ProjectStatus:
    """Map a status this contract does not know onto `unknown`.

    A module-level function rather than logic inlined in the validator, because
    both entry points into this DTO need the identical rule: the `before`
    validator below (which is what survives FastAPI's re-validation against
    `response_model`) and `from_domain`, whose `item.status` is a plain domain
    `str`. Sharing the function is what keeps them from drifting apart.
    """
    if not isinstance(value, str):
        return ProjectStatus.UNKNOWN
    try:
        return ProjectStatus(value)
    except ValueError:
        return ProjectStatus.UNKNOWN


class ProjectItemDto(BaseModel):
    """One feed row on the wire.

    All nine fields projects_list.yaml declares required
    (#/components/schemas/ProjectItem), each forwarded from the domain
    `ProjectItem` unchanged -- this layer serializes, it derives nothing.

    `title` is `str | None` because the contract leaves it out of `required` and a
    manually created document has none. This is the layer where that widening is
    *enforced* rather than merely declared: Pydantic raises on an untitled row
    under a narrow `title: str`, which the domain's own annotation cannot do.

    `retryable` is declared `bool` rather than left to coercion: `False == 0` in
    Python, so an `int`-typed field would emit `0`/`1` and still satisfy a
    value-only equality.

    Timestamps are *converted* to UTC, not echoed: a row stored at `+07:00` names
    the same instant as its UTC form, but the contract declares one wire form, and
    a client parsing offsets it was never told to expect is a client the contract
    did not describe. A naive value is refused instead -- see `_as_utc`.

    Still absent: `page`, `limit` and `total` on the envelope below -- they arrive
    with their own scenario.
    """

    kind: ProjectKind
    id: UUID
    title: str | None
    preview: str
    document_type: str
    status: ProjectStatus
    retryable: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("status", mode="before")
    @classmethod
    def _fail_closed_to_unknown(cls, value: object) -> ProjectStatus:
        """Apply `_to_status` on *every* construction of this DTO.

        A `before` validator rather than a translation inside `from_domain` alone,
        because it must hold including on the re-validation FastAPI performs
        against `response_model`, which a from_domain-only mapping would not
        survive.

        Deliberately a mapping and not a rejection. `ProjectItemDto` is built once
        per row with no isolation, so a constrained field that raised here would
        send its `ValidationError` into the catch-all handler and cost the caller
        the entire page for one bad row. It applies to both UNION arms: documents
        allow only `draft` today while the contract can emit `ready`, so the
        document arm needs the rule as much as the generation arm.
        """
        return _to_status(value)

    @field_validator("created_at", "updated_at")
    @classmethod
    def _as_utc(cls, value: datetime, info: ValidationInfo) -> datetime:
        """Convert to UTC, refusing a naive value rather than guessing its zone.

        The guard is not redundant with the conversion: `astimezone(UTC)` does not
        raise on a naive datetime, it reads it as the *host's* local time. That
        turns a visible violation -- an offset-less string -- into an invisible
        one: a well-formed `Z` naming the wrong instant, correct in a UTC
        container and silently shifted on a developer machine.
        """
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def from_domain(cls, item: ProjectItem) -> "ProjectItemDto":
        return cls(
            # Converted at the call rather than left to Pydantic's coercion, so
            # that the two enums' differing policies are visible here: `kind`
            # raises on an unrecognised value (a bug in this process -- see its
            # docstring), `status` fails closed onto `unknown` (data a future
            # migration may widen).
            kind=ProjectKind(item.kind),
            id=item.id,
            title=item.title,
            preview=item.preview,
            document_type=item.document_type,
            status=_to_status(item.status),
            retryable=item.retryable,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class ProjectPageDto(BaseModel):
    """The feed envelope: the page, and the counters needed to page it.

    `total` is forwarded from the domain page, never derived from `len(items)` --
    under offset paging that is the size of the window, not of the set, and a
    client using it to decide whether a page 2 exists would stop one page early
    on every full page.
    """

    items: list[ProjectItemDto]
    page: int
    limit: int
    total: int

    @classmethod
    def from_domain(cls, page: ProjectPage) -> "ProjectPageDto":
        return cls(
            items=[ProjectItemDto.from_domain(item) for item in page.items],
            page=page.page,
            limit=page.limit,
            total=page.total,
        )
