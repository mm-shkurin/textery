from uuid import UUID

import pytest

from document.document import Document
from document.title_update import TitleUpdate
from statements.save_document_statements import AUTOSAVE_CONTENT, SaveStatements

STORED_TITLE = "Привет Мир"

# The one intent table, owned here rather than restated per test method. Both
# arms of `_title_intent` -- the value-object call sites and the raw wire string
# the PUT route sends -- answer to the SAME spec, so they must read it from the
# same place. Copied per test, the two tables drift in silence: a copy claiming
# blank means "clear" next to one claiming "preserve" fails only one of the two
# tests, and the suite then asserts both halves of a contradiction.
TITLE_INTENT_CASES = [
    pytest.param("", TitleUpdate.preserve(), id="empty_title_preserves"),
    pytest.param("   ", TitleUpdate.preserve(), id="whitespace_title_preserves"),
    pytest.param(" Отчёт ", TitleUpdate.of(" Отчёт "), id="padded_title_verbatim"),
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
            title=TitleUpdate.of(STORED_TITLE),
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

    def assert_forwarded_title_update(self, expected: TitleUpdate) -> None:
        # The WHOLE recorded sequence, not just the last entry: the setup save
        # forwards `of(STORED_TITLE)` and the autosave forwards the value under
        # test, so pinning both also pins the call count -- a usecase that
        # mangled the setup title, or forwarded twice per call, would otherwise
        # still pass on a `[-1]` read.
        expected_sequence = [TitleUpdate.of(STORED_TITLE), expected]
        assert self.repository.title_updates == expected_sequence, (
            f"expected {expected_sequence!r} forwarded to the repository, "
            f"got {self.repository.title_updates!r}"
        )
