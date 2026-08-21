"""`POST /api/v1/analytics/events` — the product's only tokenless write.

Everything unusual about this route follows from that one fact:

* The body is read as BYTES and parsed here, not by FastAPI's model binding. The
  bound is on bytes actually read, never on the declared `Content-Length`
  (§3.4) -- a header claiming 10 is not a promise, and a route that trusts it
  absorbs whatever the caller actually sends.
* Every refusal is the canonical `{error_code, message}` envelope with a fixed
  message. Pydantic's 422 echoes the rejected input, and this endpoint's errors
  reach anyone with a socket.
* The token is OPTIONAL but never IGNORED. No header is an anonymous event
  (§1.1); a header that is present and unusable is refused rather than quietly
  downgraded to anonymous (§1.3), because a downgrade would silently detach
  events from the account that produced them.
"""

import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError

from analytics.analytics_error_codes import (
    INVALID_PAYLOAD_MESSAGE,
    REQUEST_BODY_TOO_LARGE,
    REQUEST_BODY_TOO_LARGE_MESSAGE,
)
from analytics.analytics_payload import INVALID_PAYLOAD
from analytics.client_context import client_ip_of
from analytics.record_analytics_event import RecordAnalyticsEvent
from analytics.transport_settings import max_body_bytes
from dto.analytics.record_event_request_dto import RecordEventRequestDto
from router import api_routes
from security.current_owner import get_optional_owner_id
from shared.exceptions import ValidationException

router = APIRouter(prefix=api_routes.ANALYTICS, tags=["analytics"])


def get_record_analytics_event_usecase() -> RecordAnalyticsEvent:
    raise NotImplementedError("wired by the application composition root")


@router.post("/events", status_code=204)
async def record_event(
    request: Request,
    usecase: RecordAnalyticsEvent = Depends(get_record_analytics_event_usecase),
    owner_id: UUID | None = Depends(get_optional_owner_id),
) -> Response:
    reported = _parsed(await _body_within_bounds(request))
    await usecase.execute(
        user_id=owner_id,
        event_name=reported.event_name,
        visitor_id=reported.visitor_id,
        occurrence_key=reported.occurrence_key,
        payload=reported.payload,
        degraded=reported.degraded,
        source=_source_of(request),
    )
    # 204, not 202: the row is committed before this returns and is readable on
    # another connection by then, which is what makes the read-after-write
    # guarantee assertable instead of an unstated staleness window.
    return Response(status_code=204)


async def _body_within_bounds(request: Request) -> bytes:
    """The request body, refused as soon as it exceeds the bound.

    Accumulated from the stream and checked per chunk, so an oversized body is
    refused on the bytes ACTUALLY READ (§3.4). Checking `Content-Length` instead
    would trust a number the caller chose, and reading the whole body first would
    mean the bound never prevented anything.
    """
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_body_bytes():
            raise ValidationException(
                message=REQUEST_BODY_TOO_LARGE_MESSAGE, error_code=REQUEST_BODY_TOO_LARGE
            )
    return bytes(body)


def _parsed(body: bytes) -> RecordEventRequestDto:
    """The reported event, or the canonical refusal.

    A body that is not JSON at all answers the canonical 400 here rather than
    FastAPI's `{"detail": ...}` 422 -- the residual `endpoints.md` names as "not
    owned by this contract". Reading the body ourselves is what lets this route
    answer in the product's own envelope; the message still names no value.
    """
    try:
        return RecordEventRequestDto(**json.loads(body))
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        TypeError,
        ValidationError,
    ) as error:
        raise ValidationException(
            message=INVALID_PAYLOAD_MESSAGE, error_code=INVALID_PAYLOAD
        ) from error


def _source_of(request: Request) -> str:
    """The rate-limit bucket's subject: the caller's address, one-way hashed.

    Hashed because these counters must not become a permanent visitor log
    (`03_Security_Tests.md` §5.2, §5.4): the limiter needs to tell two callers
    apart, which a digest does, and never needs to know who either of them is.
    """
    client_ip = client_ip_of(request) or ""
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:32]
