import pytest

from document.title_update import TitleUpdate
from dto.document.document_dtos import SaveDocumentRequestDto


@pytest.mark.skip(
    reason="RED: SaveDocumentRequestDto.title_update() reads model_fields_set, which "
    "model_dump()/model_validate() does not round-trip -- an absent title reparses as clear()"
)
class TestSaveDocumentRequestDtoRoundTrip:
    """The absent-title intent must survive a serialize/parse round-trip.

    `title_update()` reads `model_fields_set`, and `model_fields_set` records how
    THIS Python object was BUILT -- not what the client sent. The two coincide
    only while the DTO is constructed exactly once, straight from the request
    body, and never re-created from its own data.

    Measured against HEAD, the coincidence already breaks under the most ordinary
    spelling there is:

        d = SaveDocumentRequestDto(content='c', version=1)
        d.title_update()                                    -> preserve()
        d.model_dump()                                      -> {..., 'title': None, ...}
        SaveDocumentRequestDto.model_validate(d.model_dump()).title_update()  -> clear()

    `model_dump()` emits `title: None` explicitly, so parsing that dump puts
    `title` INTO `model_fields_set` and the absent row is re-read as the null row.
    The content-only autosave -- the shape `documentApi.ts` sends on every
    keystroke batch -- turns into a title erasure. `model_dump(exclude_unset=True)`
    and `model_copy()` both survive; the destructive spelling is the default one.

    The same trap fires without any serialization at all: passing the field's own
    declared default, `SaveDocumentRequestDto(content='c', version=1, title=None)`,
    means CLEAR, while omitting the kwarg means PRESERVE. The safest-LOOKING
    spelling is the erasing one, which is why this cannot be left to reviewer
    discipline.

    Nothing round-trips this DTO in the codebase today (`backend/`, `acceptance/`
    and `frontend/` all grepped), so this pins a guard gap, not a live bug. The
    incident it forecloses is the day someone adds a save queue, an offline
    outbox, a request replay or a BFF hop between the route and the port: every
    content-only autosave silently becomes an erasure, and the whole existing
    suite stays green, because every current assertion reaches `title_update()`
    through HTTP against a freshly parsed request. This is the first test to call
    it directly, and calling it directly is the entire point.

    Expected values are literal `TitleUpdate.preserve()` on BOTH sides rather than
    a `before == after` comparison: a round-trip equality alone would also be
    satisfied by a DTO that erased the distinction in both directions.
    """

    def test_should_read_an_absent_title_as_preserve_after_a_dump_and_reparse(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1)

        reparsed = SaveDocumentRequestDto.model_validate(request.model_dump())

        assert request.title_update() == TitleUpdate.preserve(), (
            f"a directly-built absent title must read as preserve, got {request.title_update()}"
        )
        assert reparsed.title_update() == TitleUpdate.preserve(), (
            f"the reparsed absent title must still read as preserve, got {reparsed.title_update()}"
        )
        # The round-trip's other two fields, pinned so a dump that dropped or
        # coerced them cannot pass a test whose name promises a faithful reparse.
        assert reparsed.content == "<p>saved</p>", f"content did not survive the round-trip, got {reparsed.content!r}"
        assert reparsed.version == 1, f"version did not survive the round-trip, got {reparsed.version!r}"
