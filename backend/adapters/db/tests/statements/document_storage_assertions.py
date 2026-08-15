from document.document import Document
from statements.document_page_settings_assertions import DocumentPageSettingsAssertions


class DocumentStorageAssertions(DocumentPageSettingsAssertions):
    """The assertion half of the document storage DSL.

    Split off the statements half (`DocumentCoreStatements` subclasses this) so
    the arrange and act methods stay readable next to the post-CAS row assertions
    without the file crossing the 200-line cap.

    The assertions are a linear inheritance chain rather than one class, for the
    same cap: `DocumentRowAssertions` holds the two primitives every document
    assertion is built from, `DocumentPageSettingsAssertions` holds scenario 2.1's
    page-settings and column guards, and this class holds the post-CAS row
    assertions. Chained rather than composed so every call site stays
    `document_storage_statements.assert_*` with nothing to reach through, and so
    each name resolves in exactly one place.
    """

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

        The four overrides below are exactly the SET list. Everything else is
        carried over from the pre-save document by `_expected_like`, which is what
        makes an over-broad SET list (a clobbered `created_at`, a reset `status`)
        observable rather than invisible.

        `page_settings` is carried over rather than defaulted for a reason: a CAS
        whose SET list clobbers the column to NULL would otherwise be compared
        against an expectation that is itself a fresh `None`, and NULL == NULL
        would certify the data loss. Sourcing it from the pre-save document means
        the day a configured document goes through this path, an over-broad SET
        list fails here.
        """
        assert actual is not None, "expected a stored document, got None"
        assert self._last_updated_at is not None, (
            "assert_stored_state requires a preceding save_content_if_version_matches"
        )
        self.assert_documents_match(
            actual,
            self._expected_like(
                original,
                title=title,
                content=content,
                version=version,
                updated_at=self._last_updated_at,
            ),
        )

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
