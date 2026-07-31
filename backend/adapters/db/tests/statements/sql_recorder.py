"""Capture the SQL an adapter call emits, and read its projection strictly.

Some adapter guarantees are invisible in the return value. `find_scope_by_id_and_owner`
returns a two-field projection whether the query selected two columns or nine and threw
seven away, so the only witness to "the scope read never materialises `content`" is the
statement itself. Same shape as the CAS-shape guards, which count statements to prove the
version comparison happens in SQL rather than in Python.

The parsing here exists so the assertion can be an equality against a known column list
instead of a substring test. `"content" not in statement` is wrong in both directions: it
passes for `SELECT *` (which reads the column without naming it) and it fires on an
unrelated `content_hash`, a `WHERE` mention, or a table called `document_contents`.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import NamedTuple

from sqlalchemy import event


class RecordedSql:
    """The statements emitted while the recorder was attached, in order."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def _record(self, conn, cursor, statement, parameters, context, executemany) -> None:
        # Whitespace-collapsed but case-preserved: the statement is quoted back in every
        # failure message, and an upper-cased blob is markedly harder to read than the SQL
        # the adapter actually wrote.
        self.statements.append(" ".join(statement.split()))

    def the_only_statement(self) -> str:
        assert len(self.statements) == 1, (
            f"expected the call to emit exactly one statement, got {len(self.statements)}: "
            f"{self.statements}"
        )
        return self.statements[0]

    def starting_with(self, verb: str) -> list[str]:
        """The recorded statements whose leading keyword is `verb`.

        Case-insensitive on the keyword only: the statements are kept case-preserved
        so they read as SQL in a failure message, but SQLAlchemy's own casing is not
        something a test should be pinning.
        """
        prefix = verb.upper() + " "
        return [sql for sql in self.statements if sql.upper().startswith(prefix)]

    def selected_columns(self) -> list[str]:
        """The bare column names in the single statement's projection.

        Qualification and labels are normalised away (`documents.id AS documents_id` ->
        `id`) so the expectation can be written as the field list it is pinning, but `*`
        normalises to `*` -- a `SELECT *` therefore fails the equality rather than
        slipping past a substring check.

        Prefer `qualified_selected_columns` for a new assertion. Dropping the qualifier
        discards the only evidence of *which* table was read, so a projection of two
        same-named columns off a joined or wrong table satisfies the equality. This
        bare form is kept for the document-scope suite, which pins it already.
        """
        return [expression.split(".")[-1] for expression in self.qualified_selected_columns()]

    def qualified_selected_columns(self) -> list[str]:
        """The projection with its table qualifier intact (`ai_edits.id`).

        Only the SQLAlchemy label is normalised away (`ai_edits.id AS ai_edits_id` ->
        `ai_edits.id`); the qualifier stays because it is the assertion's only witness
        that the columns came off the table under test. `*` normalises to `*`, so a
        `SELECT *` fails the equality rather than slipping past a substring check.
        """
        statement = self.the_only_statement()
        head = statement.upper()
        assert head.startswith("SELECT "), (
            "the scope read must be a plain SELECT whose projection can be read off the "
            f"statement; a CTE or a wrapped query would hide the columns. Got: {statement}"
        )
        select_at = len("SELECT ")
        from_at = head.find(" FROM ")
        assert from_at > select_at, f"could not find the FROM clause in: {statement}"

        columns = []
        for raw in statement[select_at:from_at].split(","):
            expression = raw.strip()
            # `col AS label` -> `col`; the label is SQLAlchemy's, not the schema's.
            without_label = expression.upper().split(" AS ", 1)[0]
            expression = expression[: len(without_label)].strip()
            columns.append(expression.replace('"', "").lower())
        return columns


class WatchedRead[T](NamedTuple):
    """What a watching action observed: the answer, and the SQL that produced it.

    Returned by the action rather than stashed on the Statements instance. A hidden
    field makes the projection assertion silently ordering-dependent on a *different*
    method having run first, and the most likely way to trip that -- calling the plain
    finder and then the compound assertion -- surfaces as "the recorder captured no
    SQL", misdiagnosing a wiring mistake as an adapter defect.

    Generic in the answer so it can live beside the recorder rather than once per
    Statements class: the pairing is the recorder's own concern, the DTO is not.
    """

    answer: T | None
    recorded: RecordedSql


@contextmanager
def recording_sql(session) -> Iterator[RecordedSql]:
    """Record every statement emitted through `session`'s engine inside the block.

    Registers on the **sync** engine explicitly. `AsyncSession.get_bind()` happens to hand
    back the sync `Engine` today, but `before_cursor_execute` never fires for a listener
    attached to an `AsyncEngine`, and that failure is silent in the direction that matters:
    zero recorded statements reads as "no SQL was emitted", which is exactly what a
    passing-looking assertion about an absent column would want.
    """
    bind = session.get_bind()
    engine = getattr(bind, "sync_engine", bind)
    recorded = RecordedSql()
    event.listen(engine, "before_cursor_execute", recorded._record)
    try:
        yield recorded
    finally:
        event.remove(engine, "before_cursor_execute", recorded._record)
