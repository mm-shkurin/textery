from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProjectItem:
    """One row of the caller's feed.

    Frozen, and therefore hashable and compared by value: scenario 1.1 asserts the
    returned multiset exactly, so a row the feed silently suppressed, invented or
    served twice has to surface as a difference rather than passing a `contains`
    check.

    All nine fields the contract declares
    (api-specs/projects_list.yaml #/components/schemas/ProjectItem) live here from
    1.1 onward, and not one of them carries a default. 1.1's own row assertion is
    the first test that reads them all: it compares the whole row `asdict` against
    the contract's literals, so a field this VO did not carry -- or carried with a
    default the usecase could silently fall back to -- fails it by name. A default
    would also keep `ProjectItem(id=...)` legal, which is exactly how the storage
    adapter went on emitting hollow id-only rows with every test green; the shape
    statement in the usecase tests pins that no field ever regains one.

    Values are the storage adapter's to project. This VO forbids absence; it does
    not derive anything.
    """

    kind: str
    id: UUID
    title: str
    preview: str
    document_type: str
    status: str
    retryable: bool
    created_at: datetime
    updated_at: datetime
