from datetime import datetime
from typing import Any

from document.document import Document


class DocumentRowAssertions:
    """The two primitives every document row assertion is built from.

    The bottom of the DSL chain (`DocumentRowAssertions` <-
    `DocumentPageSettingsAssertions` <- `DocumentStorageAssertions` <-
    `DocumentCoreStatements` <- `DocumentStorageStatements`). Inherited rather
    than delegated, for the same reason the chain's other links are: every call
    site stays `document_storage_statements.assert_*`, with no collaborator to
    reach through.

    Split out because both groups above -- the post-CAS row assertions and the
    page-settings ones -- compare a whole document against an expectation derived
    from a pre-operation one, and neither group owns that comparison. Keeping it
    here is also what lets the two groups sit in files under the 200-line cap.

    Owns `_last_updated_at` because this is the side that reads it; the save
    action on the statements class records into it.
    """

    def __init__(self) -> None:
        # The clock the DSL hands the CAS. Captured so `updated_at` -- the fourth
        # column the SET list writes -- can be asserted against the exact value that
        # went in, rather than left unpinned or waved through with a monotonicity check.
        self._last_updated_at: datetime | None = None

    def assert_documents_match(self, actual: Document | None, expected: Document) -> None:
        assert actual is not None, "expected a document, got None"
        # Every persisted field, so a column that silently fails to round-trip
        # (as `title` did before it was listed here) cannot hide behind a subset.
        assert (
            actual.id,
            actual.owner_id,
            actual.document_type,
            actual.status,
            actual.title,
            actual.content,
            actual.version,
            actual.idempotency_key,
            actual.created_at,
            actual.updated_at,
            actual.page_settings,
        ) == (
            expected.id,
            expected.owner_id,
            expected.document_type,
            expected.status,
            expected.title,
            expected.content,
            expected.version,
            expected.idempotency_key,
            expected.created_at,
            expected.updated_at,
            expected.page_settings,
        ), f"stored document does not match: {actual.__dict__} != {expected.__dict__}"

    def _expected_like(self, original: Document, **overrides: Any) -> Document:
        """`original` with `overrides` applied -- the expectation both row assertions build.

        `assert_stored_state` and `assert_page_settings_round_tripped` each spelled
        out the same eleven-kwarg `reconstitute`, and in both the POINT is the
        contrast between the fields the operation changed and the fields it must
        not touch. Written out twice, that contrast was buried in six identical
        `x=original.x` pass-throughs; here each caller names only what changed and
        the rest is carried over by construction. A twelfth persisted field then
        lands in one place rather than two -- the same reason
        `assert_documents_match` lists every column in a single tuple.

        A misspelled override is not swallowed: it survives the merge as an extra
        kwarg and `reconstitute` raises `TypeError` on it.
        """
        # `dict[str, Any]`, not the inferred `dict[str, object]`: this is a kwargs
        # bundle for `reconstitute`, whose eleven parameters have eleven different
        # types, and `object` fails all of them at the splat below.
        carried_over: dict[str, Any] = {
            "id": original.id,
            "owner_id": original.owner_id,
            "document_type": original.document_type,
            "status": original.status,
            "idempotency_key": original.idempotency_key,
            "created_at": original.created_at,
            "title": original.title,
            "content": original.content,
            "version": original.version,
            "updated_at": original.updated_at,
            "page_settings": original.page_settings,
        }
        return Document.reconstitute(**(carried_over | overrides))
