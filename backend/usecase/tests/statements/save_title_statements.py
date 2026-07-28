from uuid import UUID

import pytest

from document.document import Document
from document.title_update import TitleUpdate
from statements.save_document_statements import AUTOSAVE_CONTENT, SaveStatements

STORED_TITLE = "Привет Мир"
PADDED_TITLE = " Отчёт "

# Expected intents are spelled STRUCTURALLY -- `TitleUpdate(value=...)` -- and
# never through `preserve()` / `of()`. Production reaches the port through those
# same two factories, so an expectation built from them compares a factory call
# to itself and pins nothing about what the intent actually IS. Both escapes were
# MEASURED over this diff, each leaving the whole usecase suite green at 181/181:
#
#   preserve() -> TitleUpdate(value="")  -- the db CAS writes `SET title = ''`
#                                           over a stored title on every autosave
#   of(v)      -> TitleUpdate(v.strip()) -- `title.strip() or None`, the exact
#                                           normalisation the ADR rejects
#
# The second is the one the padded case below exists to catch, so without the
# literal `value=` that case was guarding nothing. Writing the value out is what
# makes both mutations red.
PRESERVE_TITLE_UPDATE = TitleUpdate(value=None)

# What the setup save forwards across the port. Named once so the setup step and
# the assertion that re-states it cannot drift apart: they are the same fact,
# not two facts that happen to agree.
STORED_TITLE_UPDATE = TitleUpdate(value=STORED_TITLE)

# The one intent table, owned here rather than restated per test method. Both
# arms of `_title_intent` -- the value-object call sites and the raw wire string
# the PUT route sends -- answer to the SAME spec, so they must read it from the
# same place. Copied per test, the two tables drift in silence: a copy claiming
# blank means "clear" next to one claiming "preserve" fails only one of the two
# tests, and the suite then asserts both halves of a contradiction.
TITLE_INTENT_CASES = [
    pytest.param("", PRESERVE_TITLE_UPDATE, id="empty_title_preserves"),
    pytest.param("   ", PRESERVE_TITLE_UPDATE, id="whitespace_title_preserves"),
    pytest.param(PADDED_TITLE, TitleUpdate(value=PADDED_TITLE), id="padded_title_verbatim"),
]


class SaveTitleStatements(SaveStatements):
    """Save-boundary title intent: what `execute` forwards across the port."""

    async def given_a_titled_document(self, owner_id: UUID) -> Document:
        document = await self.given_a_document(owner_id)
        await self.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content=AUTOSAVE_CONTENT,
            version=1,
            title=STORED_TITLE_UPDATE,
        )
        return document

    async def when_autosaving_with_title(
        self, document: Document, owner_id: UUID, title: str
    ) -> None:
        await self.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content=AUTOSAVE_CONTENT,
            version=2,
            title=TitleUpdate.of(title),
        )

    async def when_autosaving_with_a_wire_title(
        self, document: Document, owner_id: UUID, title: str
    ) -> None:
        """The RAW wire string, handed over unwrapped -- production's own arm.

        The PUT route forwards the bare Pydantic `str | None`, so the
        `isinstance(title, str)` TRUE arm of `_title_intent` is the ONLY arm
        production ever reaches. `when_autosaving_with_title` keeps pinning the
        value-object arm; this method exists so the arm that actually ships is
        not the one covered by nothing.
        """
        await self.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content=AUTOSAVE_CONTENT,
            version=2,
            title=title,
        )

    async def when_autosaving_without_a_title(self, document: Document, owner_id: UUID) -> None:
        """The `title` argument OMITTED -- the app's most common save.

        Every other `when_` here names a title. This one names none, which is
        what `documentApi.ts` sends today (`{content, version}`, no `title`
        key) and therefore what nearly every real call to `execute` looks like.
        It is the only way to reach the `title is None` arm of `_title_intent`,
        and it is deliberately NOT expressible through `TITLE_INTENT_CASES`:
        that table is indexed by a SUBMITTED STRING, and absence is a different
        axis, not another string value.
        """
        await self.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content=AUTOSAVE_CONTENT,
            version=2,
        )

    def assert_forwarded_title_update(self, expected: TitleUpdate) -> None:
        # The WHOLE recorded sequence, not just the last entry: the setup save
        # forwards `STORED_TITLE_UPDATE` and the autosave forwards the value
        # under test, so pinning both also pins the call count -- a usecase that
        # mangled the setup title, or forwarded twice per call, would otherwise
        # still pass on a `[-1]` read.
        expected_sequence = [STORED_TITLE_UPDATE, expected]
        assert self.repository.title_updates == expected_sequence, (
            f"expected {expected_sequence!r} forwarded to the repository, "
            f"got {self.repository.title_updates!r}"
        )
