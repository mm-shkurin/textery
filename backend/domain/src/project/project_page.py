from dataclasses import dataclass, field

from project.project_item import ProjectItem
from project.project_query import ProjectQuery
from project.project_sort import ProjectSort
from shared.exceptions import ValidationException

# Both bounds are domain constants, not `Query(ge=..., le=...)` on the route.
# A framework-level constraint answers in Pydantic's envelope; this project's
# 400s are `{error_code, message}`, and the contract names an error code per
# parameter.
PAGE_MIN = 1
PAGE_MAX = 1000
LIMIT_MIN = 1
LIMIT_MAX = 100
LIMIT_DEFAULT = 20


def _as_exact_int(value: object, error_code: str, name: str) -> int:
    """An exact decimal integer, or a refusal.

    `bool` is excluded explicitly because `isinstance(True, int)` is True in
    Python: `?page=true` coerced by a lax parser would otherwise read as page 1.
    Floats are refused rather than truncated -- `2.5` is not page 2, it is a
    client sending something this contract never described.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationException(
            message=f"{name} must be an exact decimal integer.",
            error_code=error_code,
        )
    return value


@dataclass(frozen=True)
class ProjectPageRequest:
    """The feed's paging, sorting and search parameters, validated on construction.

    Validation lives here rather than in the router so that every entry point --
    HTTP today, anything else later -- gets the same bounds. The values are
    already-parsed integers: turning `"2.5"` into a refusal is the adapter's job,
    turning `2.5` into one is this type's.
    """

    page: int = PAGE_MIN
    limit: int = LIMIT_DEFAULT
    sort: ProjectSort = field(default_factory=ProjectSort.default)
    query: ProjectQuery = field(default_factory=ProjectQuery.absent)

    def __post_init__(self) -> None:
        page = _as_exact_int(self.page, "INVALID_PAGE", "page")
        if not PAGE_MIN <= page <= PAGE_MAX:
            raise ValidationException(
                message=f"page must be between {PAGE_MIN} and {PAGE_MAX}.",
                error_code="INVALID_PAGE",
            )
        limit = _as_exact_int(self.limit, "INVALID_LIMIT", "limit")
        if not LIMIT_MIN <= limit <= LIMIT_MAX:
            raise ValidationException(
                message=f"limit must be between {LIMIT_MIN} and {LIMIT_MAX}.",
                error_code="INVALID_LIMIT",
            )

    @property
    def offset(self) -> int:
        """The row offset this page starts at.

        Computed from the validated bounds, so it cannot overflow: `PAGE_MAX` and
        `LIMIT_MAX` cap it at 99 900 by construction.
        """
        return (self.page - 1) * self.limit


@dataclass(frozen=True)
class ProjectPage:
    """One page of the feed, with the counters the contract declares required.

    `total` is the count of the caller's matching rows over the same
    deduplicated projection as `items`, read in the same snapshot -- never
    `len(items)`, which under offset paging is the size of the window rather than
    of the set.
    """

    items: tuple[ProjectItem, ...]
    page: int = PAGE_MIN
    limit: int = LIMIT_DEFAULT
    total: int = 0
