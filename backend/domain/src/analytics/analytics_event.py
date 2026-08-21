from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AnalyticsEvent:
    """One product-analytics event, as it is handed to the store.

    Frozen and compared by value: scenario 1.1 asserts the recorded row field by
    field, so an event the usecase invented, rewrote or recorded twice has to
    surface as a difference rather than pass an existence check.

    `visitor_id` and `occurrence_key` are `UUID`, not `str`. The column type is
    native `uuid` and §2.4 requires the upper-case, lower-case, braced and urn
    spellings of one identifier to resolve to one visitor -- text storage cannot
    do that, and a string kept here would reach the adapter as the four different
    values §5.6 warns about.

    Absent on purpose, each waiting for the scenario that first reads it:
    `payload` and `degraded` (§3.x and the degraded-visitor scenario), `id` (the
    store mints it), and `sequence`, which is deliberately never on this entity
    at all -- it is assigned by the database at INSERT
    (`decisions/analytics-ingest-shape-decision.md`).

    `event_name` is a plain `str` for the same reason: nothing in 1.1 refuses a
    name, and the catalogue-validating `EventName` arrives with §2.1/§2.2, which
    are the first scenarios that assert a refusal.
    """

    event_name: str
    visitor_id: UUID
    occurrence_key: UUID
    # NULL is a value here, not a missing one: an anonymous event carries no
    # account, and §1.3 forbids ever reaching this state from a token that was
    # sent but unusable.
    user_id: UUID | None
    # Assigned from the server's injected Clock. The request schema carries no
    # client timestamp at all, so there is no caller-supplied value to prefer.
    event_time: datetime
