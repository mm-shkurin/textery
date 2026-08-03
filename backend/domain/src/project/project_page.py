from dataclasses import dataclass

from project.project_item import ProjectItem


@dataclass(frozen=True)
class ProjectPageRequest:
    """The feed's paging/search parameters.

    Empty so far, and deliberately so: `page`, `limit`, `sort` and `q` are read by
    scenarios 1.2+, 2.x and 3.x, and adding them here before a test reads them
    would put unasserted bounds in the domain. The type exists now because the
    port signature `list_feed(owner_id, request)` is pinned by the feed read-model
    decision -- widening it later would cascade through every implementor.
    """


@dataclass(frozen=True)
class ProjectPage:
    """One page of the feed.

    `page`, `limit` and `total` belong to the same contract but arrive with the
    paging scenarios that assert them.
    """

    items: tuple[ProjectItem, ...]
