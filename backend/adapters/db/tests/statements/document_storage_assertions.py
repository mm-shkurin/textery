from datetime import datetime
from typing import Any

from document.document import Document
from document.page_settings import PageSettings

# Every way an Alembic upgrade() can put a value into rows that already exist.
# `alter_column` and `server_default` are in the list because adding the column
# WITH a default and dropping the default in the next statement is the same
# backfill in two steps -- and it leaves information_schema looking innocent.
_BACKFILL_MARKERS = ("op.execute", "op.bulk_insert", "alter_column", "UPDATE", "server_default")


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

        The SEVEN columns the CAS must NOT touch are pinned against the pre-save
        document, so an over-broad SET list (a clobbered `created_at`, a reset
        `status`) is observable rather than invisible.

        `page_settings` is the seventh, and it is taken from `original` rather
        than defaulted here for a reason: a CAS whose SET list clobbers the
        column to NULL would otherwise be compared against an expectation that
        is itself a fresh `None`, and NULL == NULL would certify the data loss.
        Sourcing it from the pre-save document means the day a configured
        document goes through this path, an over-broad SET list fails here.
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
            page_settings=original.page_settings,
        )
        self.assert_documents_match(actual, expected)

    def assert_page_settings_round_tripped(
        self, actual: Document | None, original: Document, expected: PageSettings
    ) -> None:
        """The configured document re-hydrates whole -- page settings AND everything else.

        `PageSettings` is a frozen dataclass, so a single `==` compares all nine
        fields and names the differing ones in the diff -- a mapper that drops
        `footer_text` fails here as loudly as one that drops everything.

        The `is not None` arm is asserted first and separately because it is the
        defect this whole test exists for: `Document.reconstitute` defaults
        `page_settings` to `None`, so a `to_domain` that never passes the twelfth
        kwarg is a perfectly VALID call. Every configured document then reads back
        unconfigured, and without this line nothing anywhere fails. The equality
        below subsumes it; it is kept because it is the one that NAMES the defect.

        Then the whole row, not just the new field. Asserting `page_settings` alone
        left the other ten columns unchecked on the one code path this story edits:
        a `to_domain` that gains the twelfth kwarg while mangling `title` or
        `updated_at` on the same edit would have read green here. The seeded
        document IS the expectation for those ten -- the seed is raw SQL that
        touches only `page_settings`, so every other column must come back exactly
        as `save_new` wrote it.
        """
        assert actual is not None, "expected a stored document, got None"
        assert actual.page_settings is not None, (
            "the stored page settings did not survive the mapper: to_domain omitted the "
            "page_settings kwarg, and reconstitute's default made that omission silent"
        )
        self.assert_documents_match(
            actual,
            Document.reconstitute(
                id=original.id,
                owner_id=original.owner_id,
                document_type=original.document_type,
                status=original.status,
                idempotency_key=original.idempotency_key,
                created_at=original.created_at,
                title=original.title,
                content=original.content,
                version=original.version,
                updated_at=original.updated_at,
                page_settings=expected,
            ),
        )

    def assert_column_is_jsonb_nullable_with_no_default(
        self, shape: tuple[str, str, str | None] | None
    ) -> None:
        """All three facts of the column's declaration, compared as one value.

        `data_type` is in here because the ADR mandates JSONB and nothing was
        pinning it: a `TEXT` column is nullable and defaultless too, and it would
        have satisfied the previous two-field shape while making every stored blob
        a string the mapper has to re-parse by hand.
        """
        assert shape is not None, "documents.page_settings does not exist"
        expected = ("jsonb", "YES", None)
        assert shape == expected, (
            "documents.page_settings must be declared "
            "(data_type='jsonb', is_nullable='YES', column_default=None), got "
            f"{shape!r}. JSONB because the ADR carries the settings unresolved from column to "
            "wire; NULLABLE because SQL NULL is how a never-configured document says so and a "
            "NOT NULL column has no way to say it; and NO server default because a "
            "`server_default=text(\"'{}'::jsonb\")` reflex writes a configured-looking empty "
            "object into every row that omits the column -- an irreversible backfill of the "
            "exact distinction this story exists to keep"
        )

    def assert_column_is_sql_null(self, stored: Any) -> None:
        """A document the write path never mentioned must sit at SQL NULL.

        Single caller, single contract, so the reason is intrinsic rather than
        passed in: unlike `assert_document_absent` below, there is no second
        caller pinning a different one.
        """
        assert stored is None, (
            "a document nobody configured must sit at SQL NULL, not at a materialized object "
            "-- a backfilled default would freeze today's preset into every document that "
            f"predates this story, irreversibly. Got {stored!r}"
        )

    # The outcomes a read of the `{}` row may legitimately produce today. `present`
    # is the answer if `to_domain` finds something to build; raising is equally
    # admissible, because `PageSettings` has nine required fields and `from_stored`
    # -- the resolver that would give `{}` a meaning -- belongs to 2.3/2.4. What is
    # NOT admissible is `absent` (the collapse this guard exists to forbid) or
    # `no-document` (the row was seeded; failing to find it is a broken fixture,
    # not an outcome).
    ADMISSIBLE_EMPTY_OBJECT_OUTCOMES = frozenset(
        {("read", "present"), ("raised", "TypeError"), ("raised", "ValueError")}
    )

    def assert_empty_object_is_not_read_as_never_configured(
        self,
        *,
        stored_empty: tuple[str, str],
        never_configured: tuple[str, str],
        stored_empty_column: Any,
        never_configured_column: Any,
    ) -> None:
        """`{}` and SQL NULL must not read back the same -- pinned by enumeration.

        The earlier form of this asserted only that the two tokens DIFFER, and that
        is satisfied by almost anything: a broken owner filter returning
        `no-document`, or any exception raised anywhere on the read path, differs
        from `("read","absent")` just as well as a correct implementation does. Of
        the five reachable tokens it excluded exactly one. The admissible set is
        enumerated instead, so the guard states the distinction without deciding,
        one scenario early, what `{}` resolves to.

        The two column values are preconditions, not the subject: asserted first so
        that "the outcomes differ" can never be bought by a seed that silently
        wrote NULL, or by a control row somebody configured.
        """
        assert stored_empty_column == {}, (
            "broken fixture: the row meant to hold a stored empty object does not hold one, so "
            f"this test is not comparing what it claims to. Column held {stored_empty_column!r}"
        )
        assert never_configured_column is None, (
            "broken fixture: the control row must sit at SQL NULL, or 'absent' below says "
            f"nothing about never-configured documents. Column held {never_configured_column!r}"
        )
        assert never_configured == ("read", "absent"), (
            "the control arm is broken: a row whose column is SQL NULL must read as an absent "
            f"page_settings. Got {never_configured}"
        )
        assert stored_empty in self.ADMISSIBLE_EMPTY_OBJECT_OUTCOMES, (
            f"reading a stored empty object produced {stored_empty}, which is not an admissible "
            f"outcome. Admissible today: {sorted(self.ADMISSIBLE_EMPTY_OBJECT_OUTCOMES)}. "
            "`('read', 'absent')` is the collapse this guard exists to forbid -- "
            "`PageSettings(**blob) if blob else None` is the path of least resistance and `{}` "
            "is falsy, which conflates 'configured to nothing' with 'never configured', the one "
            "distinction the story is about. `('read', 'no-document')` means the seeded row was "
            "not found at all, which is a broken fixture rather than a reading of `{}`"
        )

    def assert_migration_adds_the_column_without_backfilling(
        self, upgrade_source: str | None
    ) -> None:
        """The migration's `upgrade()` adds the column and touches no existing row.

        This is the arm the column-shape assertions cannot reach. A backfill
        written as data rather than as a default --
        `op.execute("UPDATE documents SET page_settings = '{}'::jsonb")`, or the
        standard Alembic idiom of adding WITH a `server_default` and then
        `alter_column(server_default=None)` -- leaves `column_default` NULL and
        `is_nullable` 'YES', and touches no row that either sibling test creates,
        because both create their rows AFTER the migration has run. Both arms stay
        green while every document that predates this story has been frozen at
        today's preset. The migration source is where that is observable.
        """
        assert upgrade_source is not None, (
            "no migration adds documents.page_settings. The column is additive and the read "
            "path has nowhere to read from until one exists"
        )
        backfills = [marker for marker in _BACKFILL_MARKERS if marker in upgrade_source]
        assert not backfills, (
            f"the page_settings migration's upgrade() contains {backfills}, which means it "
            "writes a value into rows that already exist. Those rows are exactly the documents "
            "nobody has ever configured, and SQL NULL is the only way they can say so -- a "
            "backfill spends that vocabulary on all of them at once and is not reversible. "
            "(`alter_column` and `server_default` are here because adding the column WITH a "
            "default and dropping the default afterwards is the same backfill in two steps, "
            "and it leaves information_schema looking innocent.)\n"
            f"upgrade() was:\n{upgrade_source}"
        )
        assert "add_column" in upgrade_source and "nullable=True" in upgrade_source, (
            "the page_settings migration must be a single additive nullable add_column, the "
            f"same shape as the title column's migration. upgrade() was:\n{upgrade_source}"
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
