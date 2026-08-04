from uuid import UUID

from pydantic import BaseModel

from project.project_item import ProjectItem
from project.project_page import ProjectPage


class ProjectItemDto(BaseModel):
    """One feed row on the wire.

    `id` alone, because `id` alone is what the domain `ProjectItem` carries.
    projects_list.yaml also declares kind, title, preview, document_type, status,
    retryable and the timestamps required -- each arrives with the scenario that
    first asserts it, so that its value is produced where a usecase test can reach
    it rather than invented in this serializer.
    """

    id: UUID

    @classmethod
    def from_domain(cls, item: ProjectItem) -> "ProjectItemDto":
        return cls(id=item.id)


class ProjectPageDto(BaseModel):
    """The feed envelope.

    No `page`/`limit`/`total`: `ProjectPage` carries `items` alone, and deriving a
    total from `len(items)` would be wrong under offset paging.
    """

    items: list[ProjectItemDto]

    @classmethod
    def from_domain(cls, page: ProjectPage) -> "ProjectPageDto":
        return cls(items=[ProjectItemDto.from_domain(item) for item in page.items])
