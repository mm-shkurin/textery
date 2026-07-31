"""Pure assertions for scenario 1.3 — no HTTP, no actions.

The refusal expectation is NOT restated here: it is imported from scenario 1.1's
`assert_is_the_canonical_refusal`, exactly as 1.2 does. The spec requires a
cross-document revision number to be refused indistinguishably from an absent document,
and a second copy of the envelope could drift while every scenario stayed green.
"""

from statements.ai_edit import ai_edit_revision_expectations as expected
from statements.ai_edit.ai_edit_cross_revision_probes import (
    CrossRevisionAftermath,
    CrossRevisionProbe,
)
from statements.ai_edit.ai_edit_document_state import DocumentState
from statements.ai_edit.ai_edit_guard_assertions import assert_is_the_canonical_refusal

AFTERMATH_CONTEXT = "after the refused cross-document restore"


def assert_refused_as_not_found(probe: CrossRevisionProbe) -> None:
    assert_is_the_canonical_refusal(
        probe.refusal,
        f"a restore of revision {probe.revision_number} — recorded on document "
        f"{probe.first_document_id} and asked for under document "
        f"{probe.second_document_id}, another document of the SAME owner (a 200 would "
        f"honour the revision number over the path document id; a 409 or 403 would "
        f"confirm the revision exists)",
    )


def assert_no_new_version_on_either_document(
    probe: CrossRevisionProbe, aftermath: CrossRevisionAftermath
) -> None:
    """The refusal suppressed the mutation, not merely the response.

    Both documents are pinned, not only the one in the path. The revision belongs to the
    first document, so a handler that resolved the revision number and then applied it to
    its *own* document would leave the path document untouched and pass a second-document
    check alone — and a handler that honoured the number under the second document is the
    scenario's headline failure. Neither may move.

    Each document is checked TWICE over, and the two checks fail differently on purpose:

      * against its ABSOLUTE spec-derived state — the first still at version 2 with its
        two-row revision page, the second still at version 1 with an empty one;
      * against the BASELINE captured before the probe, whole-body — `version` is the
        field the spec names, but `content` and `updated_at` ride in the same body and a
        partial restore that bumped neither number is still a mutation.

    The absolute check alone would miss a change to a field the spec does not fix; the
    relative check alone is satisfied by any world where both reads degrade together,
    including one where the seed never recorded anything.
    """
    expected.assert_is_a_once_ai_edited_document(
        aftermath.first_after, probe.seed_window, AFTERMATH_CONTEXT
    )
    expected.assert_is_a_never_edited_document(aftermath.second_after, AFTERMATH_CONTEXT)
    _assert_unchanged(probe, probe.first_before, aftermath.first_after, "first")
    _assert_unchanged(probe, probe.second_before, aftermath.second_after, "second")


def _assert_unchanged(
    probe: CrossRevisionProbe, before: DocumentState, after: DocumentState, which: str
) -> None:
    assert after.document.body == before.document.body, (
        f"expected no new version on the {which} document {before.document_id} after "
        f"the refused restore of revision {probe.revision_number} under document "
        f"{probe.second_document_id} — content, version and updated_at all as before. "
        f"before={before.document.body!r}, after={after.document.body!r}"
    )
    assert after.revisions.body == before.revisions.body, (
        f"expected the refused restore to write no revision row on the {which} document "
        f"{before.document_id} — a restore writes one in the same transaction as the new "
        f"version, so an added row is the tell that it ran and then lost the version CAS. "
        f"before={before.revisions.body!r}, after={after.revisions.body!r}"
    )
