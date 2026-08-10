"""An ApplicationClient whose transport records the requests it sends.

Scenario 2.1's identity is an ABSENT `title` key on the wire, and that identity is
manufactured by three lines of `ApplicationClient.save_document` — the `if title is
not None` that decides whether the key is put into the payload at all. Nothing
observes those lines today. A "simplify" pass writing the payload as one literal
(`{"content": ..., "version": ..., "title": title}`) sends `"title": null` instead of
omitting the key, and is INVISIBLE while `clear()` is unmapped in storage, because
absent and null then no-op identically end to end. The row silently stops being the
absent-key row and becomes the null row — and the miss surfaces later, pointing at
the erasure work that just shipped rather than at the client that drifted.

So the wire request itself has to be observable, which means catching it before it
reaches a server. That is an httpx concern, and the client layer is where httpx is
allowed to live (`tdd-rules.md`, "Acceptance Test Client Layer": Statements may not
import an HTTP library or handle requests). Statements import THIS, not httpx.

A SUBCLASS rather than a constructor parameter on ApplicationClient: the class under
observation must not gain a seam for its own test, and rebinding `_client` from a
subclass is the one route Python actually sanctions for reaching a private attribute
(co-location alone grants no access — Python has no package-private scope). It also
keeps the call one hop, so Statements call `save_document` on this object directly
instead of navigating to a wrapped one.

This class only RECORDS. It asserts nothing: the recorded requests are the subject,
and subjects are asserted in Statements.

No server is involved, so this needs no running backend — see the test class for why
it still ships with the `backend` marker.
"""

import json
from dataclasses import dataclass

import httpx

from clients.application.application_client import ApplicationClient

# Never resolved: MockTransport answers every request, so the host only has to be a
# syntactically valid base_url. `.invalid` is the RFC 2606 reserved TLD, so a leak
# out of the mock fails to resolve loudly instead of hitting someone's dev server.
RECORDING_BASE_URL = "http://recorded.invalid"
# The status every recorded call is answered with. The subject here is the REQUEST;
# the response only has to be well-formed enough that the client's own parsing and
# its DTO construction run exactly as they do against the real backend.
RECORDED_STATUS_CODE = 200


@dataclass(frozen=True)
class RecordedRequest:
    """One outgoing request, as it went onto the wire.

    `body` is parsed from `request.content` — the actual serialized bytes — and not
    from the dict the caller passed, so a key the client dropped or added between the
    two is visible here. `method` and `path` are carried so an assertion can pin that
    the body it reads belongs to the save call, rather than trusting position.
    """

    method: str
    path: str
    body: dict


class RecordingApplicationClient(ApplicationClient):
    """A real ApplicationClient that dispatches into a recorder instead of a server."""

    def __init__(self) -> None:
        super().__init__()
        self._recorded_requests: list[RecordedRequest] = []
        # Fails loudly if `ApplicationClient` renames its transport attribute. Without
        # this, the rebinding below would quietly create a NEW unused attribute and
        # every request would go to a real localhost backend instead of the recorder —
        # surfacing as a connection error three layers away from its cause.
        assert hasattr(self, "_client"), (
            "RecordingApplicationClient rebinds ApplicationClient._client to record "
            "requests; that attribute no longer exists, so the recorder is not wired in"
        )
        # The httpx.AsyncClient built by ApplicationClient.__init__ is replaced before
        # any request is made. It is lazy — no connection is ever opened — but it is
        # closed with the recorder anyway rather than leaked.
        self._discarded = self._client
        self._client = httpx.AsyncClient(
            base_url=RECORDING_BASE_URL,
            transport=httpx.MockTransport(self._record),
        )

    @property
    def recorded_requests(self) -> list[RecordedRequest]:
        """Every request sent through this client, in dispatch order."""
        return list(self._recorded_requests)

    def _record(self, request: httpx.Request) -> httpx.Response:
        self._recorded_requests.append(
            RecordedRequest(
                method=request.method,
                path=request.url.path,
                body=json.loads(request.content),
            )
        )
        return httpx.Response(RECORDED_STATUS_CODE, json={})

    async def close(self) -> None:
        await super().close()
        await self._discarded.aclose()
