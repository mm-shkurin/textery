"""Pure assertions for scenario 1.2 — no HTTP, no actions.

The refusal expectation is NOT restated here: it is imported from scenario 1.1's
`assert_is_the_canonical_refusal`. The spec requires a cross-document edit id to be
refused indistinguishably from an absent document, and two independently written
expectations could drift apart while both stayed green — the shared anchor is the
assertion.
"""

from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit.ai_edit_cross_document_probes import CrossDocumentProbe
from statements.ai_edit.ai_edit_edit_states import (
    DONE_STATUS,
    ERROR_STATUS,
    STATES_REACHABLE_WITHOUT_A_CANCEL,
)
from statements.ai_edit.ai_edit_guard_assertions import assert_is_the_canonical_refusal
from statements.ai_edit.ai_edit_http_status import OK_STATUS
from statements.response_assertions import assert_iso_timestamp_within

REQUIRED_FIELDS = {"edit_id", "status", "created_at"}
KNOWN_FIELDS = REQUIRED_FIELDS | {
    "version",
    "revision_number",
    "changed",
    "error_code",
    "last_seq",
}
DONE_ONLY_FIELDS = ("version", "revision_number", "changed")


def assert_refused_as_not_found(probe: CrossDocumentProbe) -> None:
    assert_is_the_canonical_refusal(
        probe.refusal,
        f"{probe.endpoint!r} for edit {probe.edit_id} — queued on one document and "
        f"asked for under another document of the SAME owner (a 200 would honour the "
        f"edit id over the path document id; a 403 would confirm the edit exists)",
    )


def assert_the_edit_survived_under_its_own_document(
    probe: CrossDocumentProbe, edit_state_after: RawResponseDto
) -> None:
    """The refusal suppressed the mutation, not merely the response.

    `/cancel` is one of the three probed endpoints, so "refused" has to mean the edit
    was left alone — a handler that terminalized it and *then* refused would pass the
    404 assertion on its own. Read back through the edit's rightful path.

    Every field of `AiEditResponse` is pinned, but the two a live worker moves are pinned
    to what stays true under it rather than to a snapshot: `status` to the set of states
    reachable without a cancel, `last_seq` to a non-negative counter. The rest are exact —
    `edit_id` to the seeded id, `created_at` to the window the queue call was bracketed
    in, and the terminal-only fields to the invariant the spec states about them. A byte
    compare of the whole body would fail on a correct system; a two-field spot check
    would pass on several wrong ones.
    """
    assert edit_state_after.status_code == OK_STATUS, (
        f"expected {OK_STATUS} reading edit {probe.edit_id} back under its own document "
        f"{probe.first_document_id} after the refused {probe.endpoint!r}, got "
        f"status_code={edit_state_after.status_code}, body={edit_state_after.text!r}"
    )
    body = edit_state_after.body or {}
    _assert_carries_only_known_fields(body, probe, edit_state_after)
    _assert_identity_and_creation(body, probe, edit_state_after)
    _assert_was_not_cancelled(body, probe, edit_state_after)
    _assert_terminal_fields_match_status(body, probe, edit_state_after)


def _assert_carries_only_known_fields(
    body: dict, probe: CrossDocumentProbe, response: RawResponseDto
) -> None:
    """No field beyond the documented eight, and none of the three required ones missing.

    An extra key is the tell that matters here: a handler leaking the other document's
    id, or the raw row, would otherwise slip past every field assertion below.
    """
    unknown = set(body) - KNOWN_FIELDS
    missing = REQUIRED_FIELDS - set(body)
    assert not unknown and not missing, (
        f"expected the edit read back after the refused {probe.endpoint!r} to carry only "
        f"{sorted(KNOWN_FIELDS)} and at least {sorted(REQUIRED_FIELDS)}; unexpected="
        f"{sorted(unknown)}, missing={sorted(missing)} in body={response.text!r}"
    )


def _assert_identity_and_creation(
    body: dict, probe: CrossDocumentProbe, response: RawResponseDto
) -> None:
    assert body.get("edit_id") == probe.edit_id, (
        f"expected the edit read back under its own document to be edit "
        f"{probe.edit_id}, got body={response.text!r}"
    )
    assert_iso_timestamp_within(
        body.get("created_at"),
        f"created_at of edit {probe.edit_id}",
        probe.setup.queued_before,
        probe.setup.queued_after,
    )
    last_seq = body.get("last_seq")
    assert isinstance(last_seq, int) and not isinstance(last_seq, bool) and last_seq >= 0, (
        f"expected last_seq of edit {probe.edit_id} to be a non-negative event counter "
        f"after the refused {probe.endpoint!r}, got {last_seq!r} in body={response.text!r}"
    )


def _assert_was_not_cancelled(
    body: dict, probe: CrossDocumentProbe, response: RawResponseDto
) -> None:
    assert body.get("status") in STATES_REACHABLE_WITHOUT_A_CANCEL, (
        f"expected the refused {probe.endpoint!r} under document "
        f"{probe.second_document_id} to leave edit {probe.edit_id} in one of the states "
        f"reachable without a cancel {STATES_REACHABLE_WITHOUT_A_CANCEL}, got "
        f"status={body.get('status')!r} — the refusal answered 404 and mutated anyway "
        f"(or invented a status). body={response.text!r}"
    )


def _assert_terminal_fields_match_status(
    body: dict, probe: CrossDocumentProbe, response: RawResponseDto
) -> None:
    """The spec makes four fields conditional on `status`; assert that coupling exactly.

    This branches on the OBSERVED status because the worker owns it — but it computes no
    expected value from runtime data: each branch is a fixed literal expectation stated
    by documents_ai_edits_get.yaml.
    """
    status = body.get("status")
    if status != DONE_STATUS:
        observed = {field: body.get(field) for field in DONE_ONLY_FIELDS}
        assert observed == dict.fromkeys(DONE_ONLY_FIELDS), (
            f"documents_ai_edits_get.yaml: {list(DONE_ONLY_FIELDS)} are present only when "
            f"status is {DONE_STATUS!r}; edit {probe.edit_id} is {status!r} yet carries "
            f"{observed} in body={response.text!r}"
        )
    else:
        assert isinstance(body.get("changed"), bool), (
            f"expected a boolean `changed` on the done edit {probe.edit_id}, got "
            f"{body.get('changed')!r} in body={response.text!r}"
        )
    if status != ERROR_STATUS:
        assert body.get("error_code") is None, (
            f"documents_ai_edits_get.yaml: error_code is present only when status is "
            f"{ERROR_STATUS!r}; edit {probe.edit_id} is {status!r} yet carries "
            f"error_code={body.get('error_code')!r} in body={response.text!r}"
        )
