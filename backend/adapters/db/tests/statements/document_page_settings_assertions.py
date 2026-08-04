from typing import Any

from document.document import Document
from statements.document_migration_assertions import DocumentMigrationAssertions
from statements.document_row_assertions import DocumentRowAssertions
from statements.page_settings_fakes import configured_page_settings


class DocumentPageSettingsAssertions(DocumentRowAssertions, DocumentMigrationAssertions):
    """The scenario 2.1 assertions: page settings round-trip, and absence stays absent.

    Split from `DocumentStorageAssertions` (which subclasses this) when scenario
    2.1's five assertions carried that file 100 lines past the 200-line cap. The
    seam is not arbitrary -- these five and the post-CAS row assertions call
    nothing of each other, sharing only the two primitives both inherit from
    `DocumentRowAssertions`.

    Guard (b)'s migration arm was split off again, to
    `DocumentMigrationAssertions`, when this file crossed the same cap. It is
    mixed in rather than delegated so it stays reachable as
    `document_storage_statements.assert_migration_adds_the_column_without_backfilling`,
    like every other link in the chain.
    """

    def assert_page_settings_round_tripped(
        self, actual: Document | None, original: Document
    ) -> None:
        """The configured document re-hydrates whole -- page settings AND everything else.

        The expectation is sourced here from `page_settings_fakes` rather than passed
        in. It was a third argument the test could only ever fill one way, since the
        seed is built from that same factory -- so the test was threading a value it
        had no say over, and a call site free to pass a DIFFERENT object could only
        ever be wrong. Both halves now read the single shared definition of
        "configured".

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
        as `save_new` wrote it, which is what `_expected_like` carries over.
        """
        assert actual is not None, "expected a stored document, got None"
        assert actual.page_settings is not None, (
            "the stored page settings did not survive the mapper: to_domain omitted the "
            "page_settings kwarg, and reconstitute's default made that omission silent"
        )
        self.assert_documents_match(
            actual, self._expected_like(original, page_settings=configured_page_settings())
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
        passed in: unlike `assert_document_absent`, there is no second caller
        pinning a different one.
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
