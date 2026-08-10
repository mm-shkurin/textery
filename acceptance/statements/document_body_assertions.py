"""Act-phase assertion kit for a document response body.

Scenario 2.1 and 3.2 are the same claim about two wire shapes — a save that
carries no title intent (the key absent, or the key sent blank) must leave the
stored document otherwise correctly updated. Each row therefore does the same two
things to the response it kept: guard that the call really happened and really
succeeded, then pin the document fields it can name to literals and the two
wall-clock timestamps to mere presence.

Held once here because it is *assertion* logic, not setup: the guard and the field
pin were verbatim copies in the two rows, differing only in the noun naming the
call. `document_page_settings_read_statements` hand-rolls a third variant of the
guard against its own read; it is left alone deliberately (a different scenario,
its own committed row) and can adopt this module when it is next touched.

Distinct from `setup_assertions.assert_setup_ok`, which pins ARRANGE calls and says
so in its message ("setup: ..."). These assertions are the act under test, so a
failure here must not read as a broken fixture.

Nothing here touches auth, document setup, or any scenario constant, so it is a
plain module of functions rather than a mixin.
"""

# The only two response fields whose values are wall-clock and so unpinnable. Their
# presence is not — an omitted timestamp is a shape regression the field pins cannot
# see, because those compare only the keys they name.
TIMESTAMP_FIELDS = frozenset({"created_at", "updated_at"})


def body_of_successful_response(response, described_as: str) -> dict:
    """The guard half of every pin below: the arrange really ran, and the call really
    succeeded. Without both, the body would fall back to {} and every field pin would
    compare None against its expectation — failing for the wrong reason.

    `described_as` is an article-free noun phrase naming the call, e.g.
    "content-only save"."""
    assert response is not None, f"arrange did not run: no {described_as}"
    assert response.status_code == 200, (
        f"expected the {described_as} to succeed with 200, got "
        f"status_code={response.status_code}, body={response.body}"
    )
    return response.body or {}


def assert_document_body(body: dict, expected: dict, described_as: str) -> None:
    """Pin the named document fields to exact values, and both timestamps to presence.

    The whole nameable write shape is compared rather than the one field under test:
    a green that preserves a title by REFUSING, short-circuiting, or only partially
    applying the save would satisfy a title-only assertion and fails here instead.

    `described_as` is an article-free noun phrase naming the operation that left the
    body, e.g. "content-only autosave"."""
    assert {key: body.get(key) for key in expected} == expected, (
        f"expected the {described_as} to leave {expected!r}, got body={body!r}"
    )
    assert TIMESTAMP_FIELDS <= body.keys(), (
        f"expected the body left by the {described_as} to carry both timestamps, "
        f"got body={body!r}"
    )
