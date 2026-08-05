from uuid import UUID

from pydantic import BaseModel

from project.project_item import ProjectItem
from project.project_page import ProjectPage


class ProjectItemDto(BaseModel):
    """One feed row on the wire.

    `id` alone. The domain `ProjectItem` now carries all nine fields
    projects_list.yaml declares required, but nothing yet asserts them on the
    *wire*: serializing a field here would emit whatever the storage adapter
    happens to hold, and today that is a placeholder, not a projection. Each field
    is added to this DTO by the scenario that first asserts it in the envelope.
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
