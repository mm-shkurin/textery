from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProjectItem:
    """One row of the caller's feed.

    Frozen, and therefore hashable and compared by value: scenario 1.1 asserts the
    returned multiset exactly, so a row the feed silently suppressed, invented or
    served twice has to surface as a difference rather than passing a `contains`
    check.

    `id` alone is the identity here. `kind` -- and with it the whole
    document/generation discriminator -- is absent because no assertion in 1.1
    reads it; scenario 1.8 ("a document and a generation sharing an id are two
    distinct items") is the first test that does, and it adds the field. The
    contract's other fields (title, preview, document_type, status, retryable, the
    timestamps) are likewise deferred to the scenario that first asserts one.
    """

    id: UUID
