import pytest

from document.title_update import TitleUpdate
from dto.document.document_dtos import SaveDocumentRequestDto


@pytest.mark.skip(
    reason="RED: SaveDocumentRequestDto.title_update() reads model_fields_set, which "
    "neither model_dump()/model_validate() nor model_dump_json()/model_validate_json() "
    "round-trips -- an absent title reparses as clear() on BOTH legs"
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
        # The round-trip's other fields, pinned so a dump that dropped or coerced
        # them cannot pass a test whose name promises a faithful reparse. `title`
        # is pinned too: `title_update()` reading preserve while the field itself
        # came back as a string would be a reparse this test must not call faithful.
        assert reparsed.content == "<p>saved</p>", (
            f"content did not survive the round-trip, got {reparsed.content!r}"
        )
        assert reparsed.title is None, (
            f"an absent title must reparse as the None field value, got {reparsed.title!r}"
        )
        assert reparsed.version == 1, (
            f"version did not survive the round-trip, got {reparsed.version!r}"
        )

    def test_should_read_an_absent_title_as_preserve_after_a_json_dump_and_reparse(self):
        """The JSON leg -- the one every incident this class names actually travels.

        A save queue, an offline outbox, a request replay and a BFF hop all
        persist or forward JSON, not a live Python dict. And in Pydantic v2
        `model_dump_json()` does NOT route through the Python `model_dump`
        method: it goes straight to the Rust serializer. So the two legs are
        separably fixable -- a writer-side green (`exclude_unset` by default, a
        `@model_serializer` that drops unset fields) turns the dict leg above
        green while leaving THIS one erasing. Measured at HEAD both legs are
        broken identically; pinning only the dict leg would hand green the
        freedom to fix the leg that no incident travels.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1)

        reparsed = SaveDocumentRequestDto.model_validate_json(request.model_dump_json())

        assert request.title_update() == TitleUpdate.preserve(), (
            f"a directly-built absent title must read as preserve, got {request.title_update()}"
        )
        assert reparsed.title_update() == TitleUpdate.preserve(), (
            "the JSON-reparsed absent title must still read as preserve, "
            f"got {reparsed.title_update()}"
        )
        assert reparsed.content == "<p>saved</p>", (
            f"content did not survive the JSON round-trip, got {reparsed.content!r}"
        )
        assert reparsed.title is None, (
            f"an absent title must reparse as the None field value, got {reparsed.title!r}"
        )
        assert reparsed.version == 1, (
            f"version did not survive the JSON round-trip, got {reparsed.version!r}"
        )


class TestSaveDocumentRequestDtoFromALiteralBody:
    """A body nobody serialized: the reader read alone, with no writer to blame.

    Deliberately NOT part of the round-trip class above, and deliberately NOT
    skipped -- because it PASSES at HEAD. Nothing here is derived from
    `model_dump()`; the dict is hand-written and simply has no `title` key, the
    shape a BFF hop, a `model_construct` rebuild or a hand-assembled queue
    payload produces. `model_fields_set` therefore never gains `title` and the
    row already reads as preserve.

    Its job is to constrain GREEN, not to fail. The round-trip class can be
    turned green from the WRITER side; this one cannot be touched by any
    serializer change at all, so it is the assertion that survives to say what
    the reader must mean. It also forecloses the over-correcting green -- one
    that stops distinguishing absent from null by making absent CLEAR -- which
    would satisfy a round-trip equality while erasing exactly the intent the
    round-trip class exists to protect. Live from the first commit: a guard
    parked behind the RED skip marker guards nothing while the bug is present.
    """

    def test_should_read_a_body_with_no_title_key_as_preserve(self):
        request = SaveDocumentRequestDto.model_validate({"content": "<p>saved</p>", "version": 1})

        assert request.title_update() == TitleUpdate.preserve(), (
            "a body carrying no title key at all must read as preserve, "
            f"got {request.title_update()}"
        )
        assert request.content == "<p>saved</p>", (
            f"content did not survive parsing, got {request.content!r}"
        )
        assert request.title is None, (
            f"a body with no title key must parse to the None field value, got {request.title!r}"
        )
        assert request.version == 1, (
            f"version did not survive parsing, got {request.version!r}"
        )
