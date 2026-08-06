from uuid import UUID

from fastapi import APIRouter, Depends, Response

from dto.project.project_response_dto import ProjectPageDto
from project.list_projects import ListProjects
from project.project_page import ProjectPageRequest
from security.current_owner import get_current_owner_id

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_list_projects_usecase() -> ListProjects:
    raise NotImplementedError("wired by the application composition root")


@router.get("", response_model=ProjectPageDto)
async def list_projects(
    response: Response,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ListProjects = Depends(get_list_projects_usecase),
) -> ProjectPageDto:
    """The caller's own feed.

    `owner_id` is a predicate resolved from the Bearer token, never a request
    parameter: the read is scoped to the caller by construction, so no query
    string can widen it. The dependency raises before this body runs when the
    header is missing, so an unauthenticated request never reaches the port.

    `ProjectPageRequest()` is built with no arguments because it carries none yet
    -- page, limit, sort and q arrive with the paging and search scenarios.
    """
    # Per-account content behind a shared CDN/proxy: no-store keeps one caller's
    # feed out of a response cache another caller could be served from.
    response.headers["Cache-Control"] = "no-store"
    page = await usecase.execute(owner_id=owner_id, request=ProjectPageRequest())
    return ProjectPageDto.from_domain(page)
