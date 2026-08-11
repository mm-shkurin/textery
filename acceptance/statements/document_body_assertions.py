"""Act-phase assertion kit for a document response body.

Scenario 2.1 and 3.2 are the same claim about two wire shapes — a save that
carries no title intent (the key absent, or the key sent blank) must leave the
stored document otherwise correctly updated. Each row therefore does the same two
things to the response it kept: guard that the call really happened and really
succeeded, then pin the document fields it can name to literals and the two
wall-clock timestamps to the window this test run occupies.

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

from datetime import datetime, timedelta, timezone

# The two response fields the caller cannot pin to a literal, because the value is
# taken from the server's wall clock. Not "unpinnable": a stamp is BOUNDABLE, and
# these are bounded below. Naming them here keeps them out of every caller's
# `expected` dict while still making them part of the compared key set.
TIMESTAMP_FIELDS = frozenset({"created_at", "updated_at"})
# How far back a stamp may sit and still belong to this test's own run. The whole
# arrange is a handful of HTTP round trips against a local server, so anything older
# came from a fixed epoch, a seeded fixture, or a previous run -- all of which a mere
# presence check waves through.
MAX_STAMP_AGE = timedelta(minutes=2)
# The server stamps with its own clock, which may sit a little ahead of the runner's.
# Slack for that, and no more: a stamp further into the future is a defect, not skew.
CLOCK_SKEW_TOLERANCE = timedelta(seconds=5)


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


def _parsed_timestamp(body: dict, field: str, described_as: str) -> datetime:
    raw = body[field]
    try:
        stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise AssertionError(
            f"expected {field} on the {described_as} to be an ISO-8601 timestamp, "
            f"got {raw!r}"
        )
    # A naive stamp is UTC by contract (the route declares date-time and SystemClock
    # stamps `datetime.now(UTC)`); attaching the zone keeps the window comparison from
    # raising on mixed awareness instead of failing with a readable message.
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def assert_document_timestamps(
    body: dict, described_as: str
) -> tuple[datetime, datetime]:
    """Bound both stamps to this run's window and order them.

    Key-set equality already proves the two keys are PRESENT; that is the shape
    question. This is the value question, and it is a separate one -- a `created_at`
    of `null`, `"N/A"`, or `1970-01-01` satisfies presence perfectly. A wall-clock
    value is not unpinnable, only unpinnable to a *literal*: it is deterministic
    within a bound, so it gets a bound rather than a shrug.

    Returns the parsed pair so callers can assert the relation their own operation
    implies."""
    now = datetime.now(timezone.utc)
    created_at = _parsed_timestamp(body, "created_at", described_as)
    updated_at = _parsed_timestamp(body, "updated_at", described_as)
    for field, stamp in (("created_at", created_at), ("updated_at", updated_at)):
        assert now - MAX_STAMP_AGE <= stamp <= now + CLOCK_SKEW_TOLERANCE, (
            f"expected {field} on the {described_as} to be stamped during this test "
            f"run, between {(now - MAX_STAMP_AGE).isoformat()} and "
            f"{(now + CLOCK_SKEW_TOLERANCE).isoformat()}, got {stamp.isoformat()}"
        )
    # True of every document on every path: it cannot have been updated before it
    # existed. The stricter save-specific relation is asserted by the function below.
    assert created_at <= updated_at, (
        f"expected the {described_as} to carry updated_at at or after created_at, got "
        f"created_at={created_at.isoformat()}, updated_at={updated_at.isoformat()}"
    )
    return created_at, updated_at


def assert_save_advanced_the_update_stamp(body: dict, described_as: str) -> None:
    """The relation a document that was CREATED and then SAVED must satisfy: the save
    took the update stamp strictly past the creation stamp.

    This is where "preserved the title by refusing the save" dies. Every other pin in
    this kit is satisfied by a document that was created correctly and then never
    touched -- content and version are compared against literals a refusing green can
    still be made to produce, but a save that never ran cannot move a clock it never
    read. `SaveDocument` stamps `updated_at=self.clock.now()` on the write path, so a
    landed save separates the two stamps by the two HTTP round trips between them.

    Kept out of `assert_document_body` deliberately: a never-saved document carries
    `updated_at == created_at` (Document.create sets them equal), so this relation
    belongs to the save rows, not to every body this kit ever compares."""
    created_at, updated_at = assert_document_timestamps(body, described_as)
    assert updated_at > created_at, (
        f"expected the {described_as} to advance updated_at past created_at -- equal "
        f"stamps mean the document was created but never actually saved -- got "
        f"created_at={created_at.isoformat()}, updated_at={updated_at.isoformat()}"
    )


def assert_document_body(body: dict, expected: dict, described_as: str) -> None:
    """Pin the named document fields to exact values, and both timestamps to a window.

    The whole nameable write shape is compared rather than the one field under test:
    a green that preserves a title by REFUSING, short-circuiting, or only partially
    applying the save would satisfy a title-only assertion and fails here instead.

    The key set is compared for EQUALITY, not containment, and it is compared FIRST.
    Two things follow, and neither held while these were subset checks. A key the
    caller did not name -- a leaked internal field, a mistakenly widened DTO -- fails
    instead of passing silently; for the write shape this row is the only black-box
    guard, so `owner_id` or `share_token` appearing on a save response goes red here or
    nowhere. And because the shape is already pinned when the values are compared, the
    lookup below can be `body[key]` rather than `body.get(key)`: a caller pinning a key
    to `None` (`generation_id` on a manually created document) then asserts that the key
    is PRESENT AND NULL, not merely that it is absent-or-null. Scenario 2.1 exists to
    distinguish absent from null; asserting its own fields through `.get` conflated
    exactly the two states under test.

    `described_as` is an article-free noun phrase naming the operation that left the
    body, e.g. "content-only autosave"."""
    assert body.keys() == expected.keys() | TIMESTAMP_FIELDS, (
        f"expected the body left by the {described_as} to carry exactly "
        f"{sorted(expected.keys() | TIMESTAMP_FIELDS)}, got {sorted(body.keys())}"
    )
    assert {key: body[key] for key in expected} == expected, (
        f"expected the {described_as} to leave {expected!r}, got body={body!r}"
    )
    # The caller's `expected` names every key but these two, so without this line the
    # timestamps would be the one part of the shape that is checked for existence and
    # nothing else -- the exact looseness the key-set equality above was tightened to
    # remove, surviving in the two fields that opted out of the value comparison.
    assert_document_timestamps(body, described_as)
