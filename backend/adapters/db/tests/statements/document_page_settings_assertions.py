import ast
from typing import Any

from document.document import Document
from document.page_settings import PageSettings
from statements.document_row_assertions import DocumentRowAssertions

# The only calls an additive migration needs. Anything else in upgrade() is either
# a write into existing rows or a schema change this story did not ask for.
#
# Allow-list, not a marker blocklist. The blocklist this replaces was five
# hand-picked substrings, and a backfill spelled
# `op.get_bind().execute(sa.text("update documents set page_settings = '{}'::jsonb"))`
# matched none of them -- lowercase `update`, and the call is not spelled
# `op.execute`. An allow-list has no such gap: an escape has to be a call nobody
# thought to name, and those fail closed instead of open.
_ADDITIVE_CALLS = frozenset({"op.add_column", "sa.Column", "postgresql.JSONB", "sa.JSON"})

# Case-insensitive: `UPDATE` and `update` are the same statement to Postgres, and
# the blocklist that only knew the first is what let the reflex through.
_WRITE_KEYWORDS = ("update ", "insert ", "delete ", "merge ")


class DocumentPageSettingsAssertions(DocumentRowAssertions):
    """The scenario 2.1 assertions: page settings round-trip, and absence stays absent.

    Split from `DocumentStorageAssertions` (which subclasses this) when scenario
    2.1's five assertions carried that file 100 lines past the 200-line cap. The
    seam is not arbitrary -- these five and the post-CAS row assertions call
    nothing of each other, sharing only the two primitives both inherit from
    `DocumentRowAssertions`.
    """

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
        as `save_new` wrote it, which is what `_expected_like` carries over.
        """
        assert actual is not None, "expected a stored document, got None"
        assert actual.page_settings is not None, (
            "the stored page settings did not survive the mapper: to_domain omitted the "
            "page_settings kwarg, and reconstitute's default made that omission silent"
        )
        self.assert_documents_match(actual, self._expected_like(original, page_settings=expected))

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

    def assert_migration_adds_the_column_without_backfilling(
        self, upgrades: list[str]
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

        Every revision mentioning the column is checked, not the first one found:
        a backfill in a second revision was previously never parsed at all.
        """
        assert upgrades, (
            "no migration adds documents.page_settings. The column is additive and the read "
            "path has nowhere to read from until one exists"
        )
        assert len(upgrades) == 1, (
            f"{len(upgrades)} revisions touch documents.page_settings. The column is added once, "
            "additively -- a second revision touching it is where a backfill hides, and pinning "
            "the count is what forces it to be read rather than assumed away"
        )
        self._assert_upgrade_is_purely_additive(upgrades[0])

    @staticmethod
    def _assert_upgrade_is_purely_additive(upgrade_source: str) -> None:
        """Structural, over the parsed tree -- not a substring hunt.

        The blocklist this replaces matched five literal strings, so
        `op.get_bind().execute(sa.text("update documents set ..."))` passed all of
        them. Here the tree is walked: every call must be one the additive shape
        needs, and every string literal is scanned case-insensitively for a write
        statement. An escape now has to be a call nobody named -- which fails
        closed, where a missing marker failed open.

        Comment and docstring text is invisible to this: it walks nodes, so a
        migration that DOCUMENTS "no UPDATE, no server_default" no longer fails on
        its own prose.
        """
        tree = ast.parse(upgrade_source)
        called = {
            _dotted_name(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _dotted_name(node.func)
        }
        forbidden = sorted(called - _ADDITIVE_CALLS)
        assert not forbidden, (
            f"the page_settings migration's upgrade() calls {forbidden}. An additive column "
            f"needs only {sorted(_ADDITIVE_CALLS)} -- anything else either writes a value into "
            "rows that already exist or changes a schema this story did not ask for. Those rows "
            "are exactly the documents nobody has ever configured, and SQL NULL is the only way "
            "they can say so; a backfill spends that vocabulary on all of them at once and is "
            f"not reversible.\nupgrade() was:\n{upgrade_source}"
        )
        written = sorted(
            {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and any(keyword in node.value.lower() for keyword in _WRITE_KEYWORDS)
            }
        )
        assert not written, (
            f"the page_settings migration's upgrade() carries SQL that writes rows: {written}. "
            f"Same reason as above, reached by a different spelling.\nupgrade() was:\n"
            f"{upgrade_source}"
        )
        adds = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _dotted_name(node.func) == "op.add_column"
        ]
        assert len(adds) == 1, (
            f"expected exactly one op.add_column, got {len(adds)}. upgrade() was:\n{upgrade_source}"
        )
        target = adds[0].args[0] if adds[0].args else None
        assert isinstance(target, ast.Constant) and target.value == "documents", (
            "the add_column must target the documents table -- a revision that merely MENTIONS "
            f"page_settings while adding a column elsewhere is not this migration.\nupgrade() "
            f"was:\n{upgrade_source}"
        )
        columns = [
            node
            for node in ast.walk(adds[0])
            if isinstance(node, ast.Call) and _dotted_name(node.func) == "sa.Column"
        ]
        assert len(columns) == 1, (
            f"expected the add_column to build exactly one sa.Column, got {len(columns)}.\n"
            f"upgrade() was:\n{upgrade_source}"
        )
        keywords = {keyword.arg: keyword.value for keyword in columns[0].keywords}
        nullable = keywords.get("nullable")
        assert isinstance(nullable, ast.Constant) and nullable.value is True, (
            "the column must be nullable -- SQL NULL is the only way a never-configured "
            f"document can say so.\nupgrade() was:\n{upgrade_source}"
        )
        assert "server_default" not in keywords, (
            "the column must carry no server default: a default is the backfill in its "
            f"shortest form.\nupgrade() was:\n{upgrade_source}"
        )
        named = columns[0].args[0] if columns[0].args else None
        assert isinstance(named, ast.Constant) and named.value == "page_settings", (
            "the added column must be page_settings -- a revision that merely MENTIONS it while "
            f"adding a different column is not this migration.\nupgrade() was:\n{upgrade_source}"
        )


def _dotted_name(node: ast.expr) -> str:
    """`op.add_column` from the AST of that call's func, or "" for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""
