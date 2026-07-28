from datetime import datetime

from document.document import Document


class DocumentStorageAssertions:
    """The assertion half of the document storage DSL.

    Split off `DocumentStorageStatements` (which subclasses this) so the arrange
    and act methods stay readable next to the post-CAS row assertions without the
    file crossing the 200-line cap. This class owns `_last_updated_at` because it
    is the side that reads it; the save action records into it.
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
        ), f"stored document does not match: {actual.__dict__} != {expected.__dict__}"

    def assert_stored_state(
        self,
        actual: Document | None,
        original: Document,
        *,
        title: str | None,
        content: str,
        version: int,
    ) -> None:
        """Assert the full post-CAS row: what the save changed AND what it must not.

        A title assertion alone is satisfiable by a save that wrote the title but
        dropped the content, and -- on the preserve-on-omit path -- by a CAS that
        matched zero rows and did nothing at all. Pinning the version is what makes
        "the save actually happened" observable.

        The CAS SET list writes FOUR columns (content, version, updated_at, and
        conditionally title). Pinning three of them left `updated_at` unverified in
        every test using this method: a CAS that dropped it from the SET list, or
        wrote the wrong clock, stayed green. It is asserted against the exact value
        the DSL generated for the last save -- category 2 "capturable from setup",
        not a monotonicity bound, because the DSL owns that clock and knows it.

        The six columns the CAS must NOT touch are pinned against the pre-save
        document, so an over-broad SET list (a clobbered `created_at`, a reset
        `status`) is observable rather than invisible.
        """
        assert actual is not None, "expected a stored document, got None"
        assert self._last_updated_at is not None, (
            "assert_stored_state requires a preceding save_content_if_version_matches"
        )
        expected = Document.reconstitute(
            id=original.id,
            owner_id=original.owner_id,
            document_type=original.document_type,
            status=original.status,
            idempotency_key=original.idempotency_key,
            created_at=original.created_at,
            title=title,
            content=content,
            version=version,
            updated_at=self._last_updated_at,
        )
        self.assert_documents_match(actual, expected)

    def assert_document_absent(self, actual: Document | None, why: str) -> None:
        """A read that must come back empty -- unknown id, or another owner's row.

        `why` is required because the two callers pin different contracts: a missing
        document and a forbidden one are deliberately indistinguishable here, and the
        message is what records which of the two a given test is holding the line on.
        """
        assert actual is None, why

    def assert_save_refused(self, actual: Document | None, why: str) -> None:
        """A CAS that must have matched zero rows and returned nothing."""
        assert actual is None, why

    def assert_content_and_version(
        self, actual: Document | None, *, content: str, version: int
    ) -> None:
        """Pin the two columns a CAS outcome is read off.

        Always both: content alone cannot tell a successful write from a refused one
        that left the old bytes in place, and version alone cannot tell a write that
        advanced the counter from one that also clobbered the content.
        """
        assert actual is not None, "expected a document, got None"
        assert (actual.content, actual.version) == (content, version), (
            f"expected content={content!r} at version {version}, "
            f"got content={actual.content!r} at version {actual.version}"
        )

    def assert_distinct_documents(self, first: Document, second: Document, why: str) -> None:
        assert first.id != second.id, why
