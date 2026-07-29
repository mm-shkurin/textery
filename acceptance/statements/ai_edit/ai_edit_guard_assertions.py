"""Pure assertions for scenario 1.1 — no HTTP, no actions.

The expected 404 envelope is pinned to an exact body rather than to "some 404".
Mutual byte-identity alone is a tautology while the routes are missing: both probes
fall through to Starlette's `{"detail":"Not Found"}` and agree with each other.
Anchoring each body to the canonical envelope makes the scenario fail in RED for the
reason it exists, and it can only pass once the real guard emits the real body.
"""

from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit.ai_edit_guard_probes import DocumentAftermath, GuardProbe

NOT_FOUND_STATUS = 404
OK_STATUS = 200

# The canonical refusal every AI-edit endpoint owes for an absent OR foreign document
# (`Error {error_code, message}` in every 404 of the story-19 api-specs). The literal
# text is the one the REST error handler already emits for NotFoundException, so the
# guard reuses the existing envelope instead of inventing a story-19-only one.
EXPECTED_NOT_FOUND_BODY = {
    "error_code": "NOT_FOUND",
    "message": "The requested resource was not found.",
}

# MessagePage / RevisionPage are `{items, next_cursor}`. `next_cursor` is null on the
# last page, and an empty page is a last page — so the whole page is pinned, not just
# `items`, or an extra disclosing field would slip through unasserted.
EMPTY_PAGE = {"items": [], "next_cursor": None}


def assert_both_refused_as_not_found(probe: GuardProbe) -> None:
    _assert_is_the_canonical_refusal(
        probe.foreign,
        f"{probe.endpoint!r} against a document owned by another account "
        f"(403, or any other body, would confirm it exists)",
    )
    _assert_is_the_canonical_refusal(
        probe.absent, f"{probe.endpoint!r} against a document id that does not exist"
    )


def _assert_is_the_canonical_refusal(response: RawResponseDto, what: str) -> None:
    assert response.status_code == NOT_FOUND_STATUS, (
        f"expected {NOT_FOUND_STATUS} refusing {what}, got "
        f"status_code={response.status_code}, body={response.text!r}"
    )
    assert response.body == EXPECTED_NOT_FOUND_BODY, (
        f"expected the canonical refusal body {EXPECTED_NOT_FOUND_BODY} refusing {what}, "
        f"got body={response.text!r}"
    )


def assert_response_bodies_byte_identical(probe: GuardProbe) -> None:
    """Both bodies are already pinned to the same dict; this pins the bytes.

    Two responses can parse to an equal dict and still differ on the wire through key
    order or whitespace, and that difference is exactly the kind of accidental tell
    that distinguishes an absent document from a foreign one.
    """
    assert probe.foreign.text == probe.absent.text, (
        f"expected the foreign-document and absent-document refusals of "
        f"{probe.endpoint!r} to be byte-identical; any difference tells the caller "
        f"which documents exist. foreign={probe.foreign.text!r}, "
        f"absent={probe.absent.text!r}"
    )


def assert_no_edit_revision_or_message_created(
    probe: GuardProbe, aftermath: DocumentAftermath
) -> None:
    """Read the foreign document's own aftermath as its rightful owner.

    A queued edit records the user's instruction as a chat message (scenario 3.1's
    "the user's message is recorded in the chat history"), so an empty message page is
    the observable proof that no edit was queued — there is no edit-listing endpoint to
    read directly. The document read closes the gap the two empty pages leave: a leaked
    restore or a leaked apply would move `version`/`content` without necessarily adding
    a row, and only an unchanged document rules that out.
    """
    _assert_page_is_empty(aftermath.messages, probe, "chat message")
    _assert_page_is_empty(aftermath.revisions, probe, "revision")
    _assert_document_unchanged(probe, aftermath)


def _assert_page_is_empty(response: RawResponseDto, probe: GuardProbe, row_kind: str) -> None:
    assert response.status_code == OK_STATUS, (
        f"expected {OK_STATUS} reading the owner's own {row_kind} history after the refused "
        f"{probe.endpoint!r}, got status_code={response.status_code}, "
        f"body={response.text!r}"
    )
    assert response.body == EMPTY_PAGE, (
        f"expected exactly zero {row_kind}s on the document after {probe.endpoint!r} "
        f"was refused, i.e. the page {EMPTY_PAGE}, got body={response.text!r}"
    )


def _assert_document_unchanged(probe: GuardProbe, aftermath: DocumentAftermath) -> None:
    after = aftermath.document_after
    assert after.status_code == OK_STATUS, (
        f"expected {OK_STATUS} re-reading the owner's own document after the refused "
        f"{probe.endpoint!r}, got status_code={after.status_code}, body={after.text!r}"
    )
    assert after.body == probe.document_before.body, (
        f"expected the document to be untouched by the refused {probe.endpoint!r} — "
        f"content, version and updated_at all as before. "
        f"before={probe.document_before.body!r}, after={after.body!r}"
    )
