from typing import Any

from pydantic import BaseModel


class RecordEventRequestDto(BaseModel):
    """The reported event, typed as PERMISSIVELY as the contract requires.

    `event_name`, `visitor_id` and `occurrence_key` are `object`, not `str` and not
    `UUID`, and that is a contract decision rather than laziness
    (`endpoints.md`, "Residual this contract does not own"). A strict Pydantic
    annotation answers **422 with `{"detail": ...}` that ECHOES the rejected
    input** -- on the product's only tokenless route, whose errors reach anyone.
    Typed loosely, a bad value travels to the domain and comes back as the
    canonical `{error_code, message}` 400 that names no value.

    Unknown fields are IGNORED rather than refused (§4.4): a browser running a
    newer bundle than the server must not have its events refused by a key the
    server has not learned yet. Pydantic's default is exactly that, so the model
    sets no `extra` policy.

    Absent from this model entirely: `user_id`, `event_time`, `id` and
    `sequence`. They are server-owned, and a field a client cannot NAME is a
    field a client cannot set (§4.1-§4.3) -- stronger than validating them away,
    because there is no branch to get wrong.
    """

    event_name: object = None
    visitor_id: object = None
    occurrence_key: object = None
    payload: dict[str, Any] | None = None
    # The browser could not persist its visitor id, so this row is one page load
    # rather than one person. A client CAN set this one, deliberately: only the
    # browser knows its own storage failed, nothing downstream trusts it for any
    # decision, and Story 15 excludes the rows from unique-visitor counts.
    degraded: bool = False
