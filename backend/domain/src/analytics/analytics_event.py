from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
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

    Absent on purpose: `id` (the store mints it) and `sequence`, which is
    deliberately never on this entity at all -- it is assigned by the database at
    INSERT (`decisions/analytics-ingest-shape-decision.md`).

    `event_name` is a plain `str` for the same reason: nothing in 1.1 refuses a
    name, and the catalogue-validating `EventName` arrives with §2.1/§2.2, which
    are the first scenarios that assert a refusal.
    """

    event_name: str
    visitor_id: UUID | None
    # NULL on server-emitted rows: the key is CLIENT-minted, and an event the
    # server raised from a state transition has no client to mint one. The unique
    # index is partial (`WHERE occurrence_key IS NOT NULL`) exactly so those rows
    # sit outside it -- a non-partial index would collapse every server-emitted
    # event for one visitor into a single row.
    occurrence_key: UUID | None
    # NULL is a value here, not a missing one: an anonymous event carries no
    # account, and §1.3 forbids ever reaching this state from a token that was
    # sent but unusable.
    user_id: UUID | None
    # Assigned from the server's injected Clock. The request schema carries no
    # client timestamp at all, so there is no caller-supplied value to prefer.
    event_time: datetime
    # Absent, explicit null and `{}` all arrive here as `{}`: the column is NOT
    # NULL with a `{}` default, so Story 15 never has two spellings of "no
    # context" to handle at every read (`endpoints.md` § five decisions, 1).
    payload: dict[str, Any] = field(default_factory=dict)
    # Its own field, not a `payload` key: `payload` is free-form and stored
    # verbatim, and a marker that governs whether a row counts toward unique
    # visitors cannot live inside the blob it qualifies. True when the browser
    # could not persist its visitor id, so this visitor is one page load rather
    # than one person.
    degraded: bool = False
