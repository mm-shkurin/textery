"""The `POST /api/v1/analytics/events` call, as a base class `ApplicationClient` inherits.

A base class rather than another method on `ApplicationClient`: that file is at the
200-line cap, and this group grows with every analytics scenario. Tests still call
`client.record_analytics_event(...)` — the entry point is unchanged.

`access_token=None` sends NO `Authorization` header at all. That is not a convenience
default: the route's identity rules turn on the header's presence
(`analytics_events_create.yaml` — absent → anonymous, present-and-invalid → 401,
never downgraded), and a helper that always sent one could not express the anonymous
visitor scenario 1.1 is about.
"""

import httpx

from clients.application.dto.analytics.analytics_event_dtos import (
    AnalyticsEventRequestDto,
    AnalyticsEventResponseDto,
)


class AnalyticsApiClient:
    # Set by ApplicationClient.__init__; declared here so this class states what it
    # needs rather than relying on the subclass by accident.
    _client: httpx.AsyncClient

    async def record_analytics_event(
        self,
        request: AnalyticsEventRequestDto,
        access_token: str | None = None,
    ) -> AnalyticsEventResponseDto:
        headers = (
            {} if access_token is None
            else {"Authorization": f"Bearer {access_token}"}
        )
        response = await self._client.post(
            "/api/v1/analytics/events", json=request.to_json(), headers=headers
        )
        return AnalyticsEventResponseDto(
            status_code=response.status_code, body=_parsed_body(response)
        )


def _parsed_body(response: httpx.Response) -> object | None:
    """The body as it can best be reported, for failure messages only.

    JSON when the body is JSON, the raw text when it is not, None when the response
    carries no body (204). A non-JSON body is kept rather than dropped: a route-miss
    HTML page and an empty 204 both report as `None` otherwise, and those are the two
    answers a stored-row failure most needs told apart.
    """
    try:
        return response.json()
    except ValueError:
        return response.text or None
