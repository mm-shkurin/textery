from dto.shared.query_int import exact_int
from project.project_page import LIMIT_DEFAULT, PAGE_MIN, ProjectPageRequest
from project.project_query import ProjectQuery
from project.project_sort import ProjectSort


def parse_page_request(
    page: str | None = None,
    limit: str | None = None,
    sort: str | None = None,
    q: str | None = None,
) -> ProjectPageRequest:
    """Build the domain request from raw query-string values.

    Everything arrives as `str | None` on purpose. Declaring `page: int` on the
    route would hand parsing to Pydantic, which answers a bad value in its own
    envelope -- and this contract's 400s are `{error_code, message}` with a code
    naming the offending parameter. The bounds themselves stay in the domain;
    this function only turns text into the values the domain validates.
    """
    return ProjectPageRequest(
        page=exact_int(page, PAGE_MIN, "INVALID_PAGE", "page"),
        limit=exact_int(limit, LIMIT_DEFAULT, "INVALID_LIMIT", "limit"),
        sort=ProjectSort.parse(sort),
        query=ProjectQuery.parse(q),
    )
