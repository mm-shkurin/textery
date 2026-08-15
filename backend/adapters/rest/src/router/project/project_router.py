from uuid import UUID

from fastapi import APIRouter, Depends, Response

from dto.project.project_page_params import parse_page_request
from dto.project.project_response_dto import ProjectPageDto
from project.list_projects import ListProjects
from security.current_owner import get_current_owner_id

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_list_projects_usecase() -> ListProjects:
    raise NotImplementedError("wired by the application composition root")


@router.get("", response_model=ProjectPageDto)
async def list_projects(
    response: Response,
    page: str | None = None,
    limit: str | None = None,
    sort: str | None = None,
    q: str | None = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ListProjects = Depends(get_list_projects_usecase),
) -> ProjectPageDto:
    """The caller's own feed.

    `owner_id` is a predicate resolved from the Bearer token, never a request
    parameter: the read is scoped to the caller by construction, so no query
    string can widen it. The dependency raises before this body runs when the
    header is missing, so an unauthenticated request never reaches the port.

    The four query parameters are declared `str | None` rather than typed: see
    `parse_page_request` for why the parsing is ours and not Pydantic's.
    """
    # Per-account content behind a shared CDN/proxy: no-store keeps one caller's
    # feed out of a response cache another caller could be served from.
    response.headers["Cache-Control"] = "no-store"
    request = parse_page_request(page=page, limit=limit, sort=sort, q=q)
    feed = await usecase.execute(owner_id=owner_id, request=request)
    return ProjectPageDto.from_domain(feed)
