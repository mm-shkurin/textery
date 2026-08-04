import ast

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


class DocumentMigrationAssertions:
    """Guard (b)'s third arm: the page-settings migration is purely additive.

    Split out of `DocumentPageSettingsAssertions` when that file passed the
    200-line cap. The seam is the sharpest one in the chain: everything here reads
    Python source text and answers with the `ast` module, touching no session, no
    `Document` and no `PageSettings`. It is deliberately NOT a `DocumentRowAssertions`
    subclass -- it needs nothing from one -- so it joins the chain as a mixin rather
    than inventing a base-class dependency to sit in the line.
    """

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
