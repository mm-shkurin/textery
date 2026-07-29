from uuid import UUID

import pytest
from ai_edit_routes import (
    ALL_ROUTES,
    BODY_VALIDATING_ROUTE_IDS,
    BODY_VALIDATING_ROUTES,
    CANONICAL_CONTENT_TYPE,
    CANONICAL_REFUSAL_BYTES,
    DISCLOSING_BODIES,
    MISSING_KWARG,
    ROUTE_IDS,
    STREAM_EDIT,
)

PROBE_DOCUMENT_ID = UUID("8c7d6e5f-4a3b-4c2d-9e1f-0a9b8c7d6e5f")


class TestAiEditRoutesRefuseUnresolvableDocument:
    """Scenario 1.1: Every endpoint refuses an absent document indistinguishably
    from a foreign one — REST adapter half.

    Given an authenticated user
    And a document owned by another account
    When the caller invokes <endpoint> against it
    And the caller invokes <endpoint> against a document id that does not exist
    Then both are refused as not found
    And the two response bodies are byte-identical

    The usecase layer already answers both cases with the single id-free
    `NotFoundException(REFUSAL_MESSAGE)` (green-usecase). What is unproven is that
    the REST layer carries that one answer to the wire unchanged on all seven
    routes — that it routes them at all, that it renders the canonical envelope
    rather than Starlette's `{"detail": ...}`, that FastAPI's own body validation
    cannot answer first, and that the stream route does not open a 200
    `text/event-stream` and bury the refusal in an event frame.

    Every body assertion below compares against `CANONICAL_REFUSAL_BYTES`, never
    against another response. Starlette's unrouted-path 404 is self-consistent —
    seven missing routes agree with each other byte for byte — so a relative
    comparison is satisfied by the very state this scenario exists to rule out.
    """

    @pytest.mark.parametrize("route", ALL_ROUTES, ids=ROUTE_IDS)
    async def test_should_answer_the_canonical_not_found_envelope(self, route, refusing_app):
        response = await refusing_app.invoke(route)

        assert response.status_code == 404, (
            f"{route.name}: expected 404, got {response.status_code}: {response.text}"
        )
        assert response.headers["content-type"] == CANONICAL_CONTENT_TYPE, (
            f"{route.name}: the refusal is plain non-streaming JSON; exact, because "
            f"`application/json-seq` would satisfy a prefix check and is a streaming "
            f"type. Got {response.headers.get('content-type')!r}"
        )
        assert response.content == CANONICAL_REFUSAL_BYTES, (
            f"{route.name}: the refusal must render the project's canonical envelope "
            f"byte for byte, not {response.content!r}. Starlette's unrouted-path 404 is "
            f"`{{'detail': ...}}`, so this assertion is what separates a real refusal "
            f"from a missing route."
        )

    @pytest.mark.parametrize("route", ALL_ROUTES, ids=ROUTE_IDS)
    async def test_should_resolve_the_document_scope_from_the_path_and_the_token(
        self, route, refusing_app, owner_id
    ):
        await refusing_app.invoke(route, document_id=PROBE_DOCUMENT_ID)

        assert refusing_app.times_reached(route) == 1, (
            f"{route.name}: the route must reach its usecase exactly once; the guard "
            f"runs there, so a route that never calls it cannot have resolved anything. "
            f"await_count={refusing_app.times_reached(route)}"
        )
        expected = route.expected_scope_kwargs(PROBE_DOCUMENT_ID, owner_id)
        resolution = refusing_app.resolution_of(route)
        assert {key: resolution.get(key, MISSING_KWARG) for key in expected} == expected, (
            f"{route.name}: the usecase must be awaited with the path document id, the "
            f"token's owner id, and this route's child identifier — each already typed, "
            f"never a raw path string. Got {resolution!r}"
        )

    @pytest.mark.parametrize("route", ALL_ROUTES, ids=ROUTE_IDS)
    async def test_should_answer_every_route_with_the_one_canonical_body(self, route, refusing_app):
        response = await refusing_app.invoke(route)

        # Seven independent equalities against one literal, rather than a set of the
        # seven bodies collapsed to `len(...) == 1`: identity among the routes follows
        # from all of them matching the anchor, and a failure names which route diverged
        # instead of reporting that some unidentified pair disagreed.
        assert (response.status_code, response.content) == (404, CANONICAL_REFUSAL_BYTES), (
            f"{route.name}: every one of the seven routes owes the identical refusal, "
            f"got {response.status_code} {response.content!r}"
        )

    @pytest.mark.parametrize("route", BODY_VALIDATING_ROUTES, ids=BODY_VALIDATING_ROUTE_IDS)
    @pytest.mark.parametrize("body_kind", sorted(DISCLOSING_BODIES))
    async def test_should_resolve_before_validating_the_request_body(
        self, body_kind, route, refusing_app
    ):
        response = await refusing_app.invoke(route, json_body=DISCLOSING_BODIES[body_kind])

        assert response.status_code == 404, (
            f"{route.name}/{body_kind}: resolution precedes validation, so a document "
            f"the caller cannot claim is 404 whatever the body says — never 422, 400 or "
            f"409. Got {response.status_code}: {response.text}"
        )
        assert response.content == CANONICAL_REFUSAL_BYTES, (
            f"{route.name}/{body_kind}: the refusal body must not vary with the body "
            f"that was sent, got {response.content!r}"
        )
        assert refusing_app.times_reached(route) == 1, (
            f"{route.name}/{body_kind}: the request never reached the usecase, so "
            f"FastAPI's own body validation answered first and the 404 above is not the "
            f"guard's. The route must not declare a validated body model the guard sits "
            f"behind."
        )

    async def test_should_refuse_the_stream_without_opening_an_event_stream(self, refusing_app):
        response = await refusing_app.invoke(STREAM_EDIT)

        assert response.status_code == 404, (
            f"the stream route must refuse with a status, not a 200 carrying an error "
            f"frame. Got {response.status_code}: {response.text}"
        )
        # Indexed, not `.get(..., "")`: an absent content-type header would satisfy a
        # `"text/event-stream" not in ...` check, and absence is not proof of anything.
        # Exact equality excludes SSE by construction rather than by exclusion list.
        assert response.headers["content-type"] == CANONICAL_CONTENT_TYPE, (
            f"a refused stream must never be opened — an SSE response commits the status "
            f"line before the guard's answer is known — and the refusal is plain "
            f"non-streaming JSON. Got {response.headers.get('content-type')!r}"
        )
        assert response.content == CANONICAL_REFUSAL_BYTES, (
            f"the stream's refusal must be the same body as the other six, got {response.content!r}"
        )
