from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from project.project_item import ProjectItem
from project.project_page import ProjectPage


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

    Timestamps serialize as UTC ISO-8601 with an explicit offset (`Z`), Pydantic's
    default form for a tz-aware `datetime`.

    Still absent: `page`, `limit` and `total` on the envelope below -- they arrive
    with their own scenario.
    """

    kind: str
    id: UUID
    title: str | None
    preview: str
    document_type: str
    status: str
    retryable: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, item: ProjectItem) -> "ProjectItemDto":
        return cls(
            kind=item.kind,
            id=item.id,
            title=item.title,
            preview=item.preview,
            document_type=item.document_type,
            status=item.status,
            retryable=item.retryable,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class ProjectPageDto(BaseModel):
    """The feed envelope.

    No `page`/`limit`/`total`: `ProjectPage` carries `items` alone, and deriving a
    total from `len(items)` would be wrong under offset paging.
    """

    items: list[ProjectItemDto]

    @classmethod
    def from_domain(cls, page: ProjectPage) -> "ProjectPageDto":
        return cls(items=[ProjectItemDto.from_domain(item) for item in page.items])
