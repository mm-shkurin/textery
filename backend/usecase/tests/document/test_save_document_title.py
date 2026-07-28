"""Scenario 3.2 -- blank-title semantics at the save boundary.

Per `decisions/blank-title-semantics-decision.md`, the title field is
three-state and the states are told apart by what the client SENT, not by the
value alone. `SaveDocument.execute` owns the BLANKNESS half of that contract:
a title whose `strip()` is empty carries no title intent and must reach the
port as `TitleUpdate.preserve()`, so it lands on the CAS preserve-on-omit
branch instead of executing `SET title = ''` over a stored title. The
absent-vs-null half is the rest adapter's (`model_fields_set`) and is covered
by its own steps.

The padded case is the guard the ADR's rejection of `title.strip() or None`
demands: that normalisation maps blank to "no intent" (wanted) AND silently
trims every legitimate title (`" Отчёт "` -> `"Отчёт"`), and nothing in the
suite could previously detect it -- Scenario 3.1's `"Привет Мир"` has only an
internal space. Blankness is tested; the stored value is never rewritten.

Asserting the forwarded `TitleUpdate` rather than the fake's stored title
keeps this at the usecase's own boundary: whether "preserve" and "clear" turn
into the right SQL is the db CAS's contract, pinned in its own adapter tests.
"""

from uuid import uuid4

import pytest

from statements.save_title_statements import (
    PRESERVE_TITLE_UPDATE,
    TITLE_INTENT_CASES,
    SaveTitleStatements,
)


@pytest.fixture
def statements():
    return SaveTitleStatements()


class TestSaveDocumentTitleIntent:
    @pytest.mark.parametrize("submitted_title, expected_update", TITLE_INTENT_CASES)
    async def test_should_preserve_on_a_blank_title_and_forward_a_real_title_verbatim(
        self, statements, submitted_title, expected_update
    ):
        owner_id = uuid4()
        document = await statements.given_a_titled_document(owner_id)

        await statements.when_autosaving_with_title(document, owner_id, submitted_title)

        statements.assert_forwarded_title_update(expected_update)

    @pytest.mark.parametrize("submitted_title, expected_update", TITLE_INTENT_CASES)
    async def test_should_apply_the_same_intent_to_a_raw_wire_string(
        self, statements, submitted_title, expected_update
    ):
        """The arm production takes, which the test above does NOT execute.

        Every other call site wraps in `TitleUpdate.of(...)` before calling, so
        the `isinstance(title, str)` TRUE arm of `_title_intent` is dead to the
        suite while being the only arm the PUT route reaches. Line and branch
        coverage cannot see the gap -- a conditional expression is one statement
        with no arc -- so deleting `TitleUpdate.of(title) if isinstance(title,
        str) else` reads 100% covered and green without this test.
        """
        owner_id = uuid4()
        document = await statements.given_a_titled_document(owner_id)

        await statements.when_autosaving_with_a_wire_title(document, owner_id, submitted_title)

        statements.assert_forwarded_title_update(expected_update)

    async def test_should_forward_preserve_when_no_title_is_submitted_at_all(self, statements):
        """Absence must be spelled `preserve()`, not a bare `None`.

        The port docstring declares `None` unusable for intent -- that is the
        whole reason `TitleUpdate` exists -- yet the ABSENT case, which is what
        nearly every save in the app is, is the one call still carrying it. So
        the ambiguous value rides the most-travelled path while the named one
        rides the rare ones.

        This assertion has to live HERE, at the port boundary. `preserve()` and
        a bare `None` produce byte-identical SET clauses in the db CAS (measured
        over `2bb51a5`): the adapter reaches `new_title is None` from
        `preserve()` via `.value` and from `None` directly, so no storage test
        can go red on the difference. The forwarded OBJECT is the only place the
        two states are distinguishable, and the fake records it verbatim.

        It is not cosmetic. The pending clear path turns `SET title = NULL` into
        real behavior, and `TitleUpdate.preserve() == TitleUpdate(value=None)`
        today -- so once a second `None`-shaped meaning exists, every autosave
        that forwards the ambiguous value is a candidate mass wipe.
        """
        owner_id = uuid4()
        document = await statements.given_a_titled_document(owner_id)

        await statements.when_autosaving_without_a_title(document, owner_id)

        statements.assert_forwarded_title_update(PRESERVE_TITLE_UPDATE)
