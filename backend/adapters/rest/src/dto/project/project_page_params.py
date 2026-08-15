from project.project_page import LIMIT_DEFAULT, PAGE_MIN, ProjectPageRequest
from project.project_query import ProjectQuery
from project.project_sort import ProjectSort
from shared.exceptions import ValidationException


def _exact_int(raw: str | None, default: int, error_code: str, name: str) -> int:
    """A query-string integer parsed strictly, or a refusal.

    `int(raw)` alone is too permissive for this contract: it accepts `+1`, `_1`
    and surrounding whitespace, and `float(raw)` would accept `2.5` and `1e3`.
    The contract says exact decimal integer, so the string is checked before it
    is converted rather than after.

    An omitted parameter takes the default; a present-but-empty one does not --
    `?page=` is a client that sent the parameter and named nothing.
    """
    if raw is None:
        return default
    candidate = raw[1:] if raw.startswith("-") else raw
    if candidate == "" or not candidate.isascii() or not candidate.isdigit():
        raise ValidationException(
            message=f"{name} must be an exact decimal integer.",
            error_code=error_code,
        )
    return int(raw)


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
        page=_exact_int(page, PAGE_MIN, "INVALID_PAGE", "page"),
        limit=_exact_int(limit, LIMIT_DEFAULT, "INVALID_LIMIT", "limit"),
        sort=ProjectSort.parse(sort),
        query=ProjectQuery.parse(q),
    )
