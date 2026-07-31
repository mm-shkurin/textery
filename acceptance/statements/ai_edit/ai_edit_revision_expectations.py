"""What the two seeded documents must EXACTLY be, before the probe ever runs.

Scenario 1.3 previously proved "no new version" only relatively — `after == before` — and
a relative expectation is satisfied by a world in which the seed never worked. If the AI
edit had silently recorded nothing, `before` and `after` would still have matched and the
scenario would have been green while its own premise ("a revision recorded on the first
document") was false.

So both documents are pinned to ABSOLUTE, spec-derived values as well. Every number here
comes from documents_revisions_list.yaml, not from a runtime read:

  * a never-edited document has version 1, empty content, and a valid EMPTY revision page;
  * the FIRST mutation of a document writes TWO revisions in one transaction — revision 1
    carrying the PRE-mutation content with source `manual`, then revision 2 carrying the
    result with source `ai` — so one applied AI edit leaves version 2 and a TWO-row page,
    newest first. That is also why the seeded revision number is exactly 2, never "≥ 1".
"""

from dataclasses import dataclass
from datetime import datetime

from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit.ai_edit_document_state import DocumentState
from statements.ai_edit.ai_edit_guard_assertions import EMPTY_PAGE
from statements.response_assertions import (
    assert_iso_timestamp_within,
    parse_iso_timestamp,
)

MANUAL_SOURCE = "manual"
AI_SOURCE = "ai"
NO_NEXT_PAGE = None
REVISION_PAGE_FIELDS = {"items", "next_cursor"}
# `restored_from` is "present only when source is restore" — neither seeded revision is a
# restore, so its presence would itself be a defect and the field set is closed.
REVISION_FIELDS = {"revision_number", "version", "source", "created_at"}

BASELINE_REVISION_NUMBER = 1
SEEDED_REVISION_NUMBER = 2
VERSION_AFTER_ONE_AI_EDIT = 2


@dataclass(frozen=True)
class ExpectedRevision:
    revision_number: int
    version: int
    source: str


# Newest first, per the spec's fixed server-side order.
REVISIONS_AFTER_ONE_AI_EDIT = (
    ExpectedRevision(SEEDED_REVISION_NUMBER, VERSION_AFTER_ONE_AI_EDIT, AI_SOURCE),
    ExpectedRevision(BASELINE_REVISION_NUMBER, seed.FIRST_VERSION, MANUAL_SOURCE),
)


def assert_is_a_never_edited_document(state: DocumentState, context: str) -> None:
    """The second document: created, never touched, and deliberately revision-less.

    The empty page is asserted, not assumed. The scenario's whole point is that the
    probed revision number exists on exactly ONE of the two documents; if the seed ever
    leaked a revision onto this one, the number would legitimately exist here and the 404
    assertion would be testing something else while staying green.
    """
    body = _assert_document_body(state, seed.FIRST_VERSION, context)
    _assert_field(state, body, "content", seed.EMPTY_CONTENT, context)
    created_at = parse_iso_timestamp(body.get("created_at"), "created_at")
    updated_at = parse_iso_timestamp(body.get("updated_at"), "updated_at")
    assert updated_at == created_at, (
        f"expected the never-edited document {state.document_id} to still carry the "
        f"updated_at it was created with {context}; got created_at="
        f"{created_at.isoformat()}, updated_at={updated_at.isoformat()}"
    )
    assert state.revisions.body == EMPTY_PAGE, (
        f"expected document {state.document_id} to have NO revisions of its own "
        f"{context} — the probed revision number must exist on exactly one of the two "
        f"documents, i.e. the page {EMPTY_PAGE}, got body={state.revisions.text!r}"
    )


def assert_is_a_once_ai_edited_document(
    state: DocumentState, window: tuple[datetime, datetime], context: str
) -> None:
    """The first document: exactly one applied AI edit, so version 2 and two revisions."""
    _assert_edited_content(state, context)
    _assert_revision_page_is(state, REVISIONS_AFTER_ONE_AI_EDIT, window, context)


def _assert_edited_content(state: DocumentState, context: str) -> None:
    body = _assert_document_body(state, VERSION_AFTER_ONE_AI_EDIT, context)
    # The applied text is the model's own output and is the one value here the test
    # cannot name. It is still not checked for mere presence: the PRE-edit content is
    # known exactly (`create_document_owned_by` pins it to ""), and the edit was required
    # to report `changed: true`, so the content MUST now differ from that known value.
    assert body.get("content") != seed.EMPTY_CONTENT, (
        f"expected document {state.document_id} to hold the applied edit's content "
        f"{context} — the edit reported changed=true, so the content cannot still be the "
        f"empty string it was created with. body={state.document.text!r}"
    )


def _assert_document_body(state: DocumentState, version: int, context: str) -> dict:
    """The fields every seeded document owes, whatever its content. Returns the body."""
    body = state.document.body or {}
    assert set(body) == seed.DOCUMENT_FIELDS, (
        f"expected document {state.document_id} to carry exactly "
        f"{sorted(seed.DOCUMENT_FIELDS)} {context}, got {sorted(body)} in "
        f"body={state.document.text!r}"
    )
    _assert_field(state, body, "document_id", state.document_id, context)
    _assert_field(state, body, "document_type", seed.DOCUMENT_TYPE, context)
    _assert_field(state, body, "status", seed.DRAFT_STATUS, context)
    _assert_field(state, body, "version", version, context)
    return body


def _assert_field(
    state: DocumentState, body: dict, field: str, expected: object, context: str
) -> None:
    assert body.get(field) == expected, (
        f"expected {field}={expected!r} on document {state.document_id} {context}, got "
        f"{body.get(field)!r} in body={state.document.text!r}"
    )


def _assert_revision_page_is(
    state: DocumentState,
    expected: tuple[ExpectedRevision, ...],
    window: tuple[datetime, datetime],
    context: str,
) -> None:
    page = state.revisions.body or {}
    assert set(page) == REVISION_PAGE_FIELDS, (
        f"expected the revision page of document {state.document_id} to carry exactly "
        f"{sorted(REVISION_PAGE_FIELDS)} {context}, got {sorted(page)} in "
        f"body={state.revisions.text!r}"
    )
    assert page.get("next_cursor") is NO_NEXT_PAGE, (
        f"expected the single revision page of document {state.document_id} to be the "
        f"last page {context}, got next_cursor={page.get('next_cursor')!r} in "
        f"body={state.revisions.text!r}"
    )
    items = page.get("items")
    observed = [
        (item.get("revision_number"), item.get("version"), item.get("source"))
        for item in (items if isinstance(items, list) else [])
    ]
    wanted = [(row.revision_number, row.version, row.source) for row in expected]
    assert observed == wanted, (
        f"expected document {state.document_id} to list exactly {wanted} as "
        f"(revision_number, version, source), newest first {context} — one applied AI "
        f"edit writes the pre-edit baseline as revision "
        f"{BASELINE_REVISION_NUMBER} and its own result as revision "
        f"{SEEDED_REVISION_NUMBER}. Got {observed} in body={state.revisions.text!r}"
    )
    earliest, latest = window
    for item in items:
        assert set(item) == REVISION_FIELDS, (
            f"expected each revision of document {state.document_id} to carry exactly "
            f"{sorted(REVISION_FIELDS)} {context}, got {sorted(item)} in "
            f"body={state.revisions.text!r}"
        )
        assert_iso_timestamp_within(
            item.get("created_at"),
            f"created_at of revision {item.get('revision_number')}",
            earliest,
            latest,
        )
