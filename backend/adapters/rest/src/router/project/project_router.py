from fastapi import APIRouter

from project.list_projects import ListProjects

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def get_list_projects_usecase() -> ListProjects:
    raise NotImplementedError("wired by the application composition root")
