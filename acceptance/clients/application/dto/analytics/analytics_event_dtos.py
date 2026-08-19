"""Typed request and response for `POST /api/v1/analytics/events`.

Contract: `api-specs/analytics_events_create.yaml`. The three fields below are the
route's required set; `payload` and `degraded` are deliberately absent here because
scenario 1.1 sends neither, and the contract distinguishes "omitted", "explicit null"
and `{}` as three separate inputs — a DTO that always spelled `payload` would collapse
that distinction before the wire.

`AnalyticsEventResponseDto` keeps the status code and the body and interprets neither.
204 carries no body at all, and the preamble of `01_API_Tests.md` is explicit that
"«an event is recorded» never means «the call answered 200»" — this response is
captured so a failure message can name what the route actually answered, never as the
thing under test. `body` is therefore typed `object | None` rather than `dict | None`:
the route-miss 404 this scenario currently meets answers a JSON object, a 413 from the
transport layer can answer plain text, and a body narrowed to `dict` would have to
discard the one that was not one — exactly when the failure message needs it most.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AnalyticsEventRequestDto:
    event_name: str
    visitor_id: str
    occurrence_key: str

    def to_json(self) -> dict:
        return {
            "event_name": self.event_name,
            "visitor_id": self.visitor_id,
            "occurrence_key": self.occurrence_key,
        }


@dataclass(frozen=True)
class AnalyticsEventResponseDto:
    status_code: int
    # Parsed JSON when the body is JSON, the raw text when it is not, None when there
    # is no body at all — reported verbatim, never asserted on in this scenario.
    body: Optional[object]
