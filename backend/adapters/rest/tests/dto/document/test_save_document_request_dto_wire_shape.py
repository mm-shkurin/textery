import json

import pytest

from dto.document.document_dtos import SaveDocumentRequestDto


@pytest.mark.skip(
    reason="RED: SaveDocumentRequestDto serializes an untouched title as an explicit "
    "'title': null key, so the body it emits tells a FOREIGN consumer 'erase the "
    "title' -- the round-trip tests cannot see this, because they only ever hand "
    "the body back to this same class"
)
class TestSaveDocumentRequestDtoWireShape:
    """What the emitted body says to a reader that is not this class.

    The round-trip class next door asserts that a body this DTO wrote, read back
    by this DTO, still means preserve. That is self-consistency, and self-
    consistency is satisfiable by a PRIVATE ENCODING: a green that serializes the
    absent row as a magic marker and strips the marker on the way back in. Built
    and measured on pydantic 2.13.4 -- a `@model_serializer` writing
    `title: "\\x00__ABSENT__"` paired with an `after` validator that discards the
    marker turns all three round-trip assertions green, `reparsed.title is None`
    included, while the body on the wire carries a `title` whose value is that
    marker string. Handed to any consumer that does not share the secret -- the
    HEAD reader itself, measured -- it reads as `TitleUpdate.of('\\x00__ABSENT__')`:
    the user's title overwritten with a control character. The round-trip tests
    all pass through that.

    So this class asserts the body, not the loop: an intent the DTO never carried
    must be ABSENT from the body it writes, in the ONE spelling every JSON reader
    on earth already agrees means absent -- no key. Nothing here parses anything,
    which is the point; there is no reader whose agreement could cover for the
    writer.

    Honest scope, stated so no later reader mistakes this for more than it is:
    this is a WRITER-side pin and a writer-side green satisfies it. That is not a
    weakness of the test, it is where the defect actually lives. There is no
    reader-side red to write against the current field representation, and the
    absence is measurable rather than a matter of opinion: fed a hand-written body
    from a foreign producer, HEAD's reader is already CORRECT on every row of
    story 17's wire table --

        {content, version}                  -> preserve   (correct)
        {..., "title": null}                -> clear      (correct)
        {..., "title": ""}                  -> preserve   (correct)
        {..., "title": "   "}               -> preserve   (correct)
        {..., "title": " Отчёт "}           -> of(" Отчёт ") verbatim (correct)
        model_construct(content=, version=) -> preserve   (correct)

    -- because absent-vs-null IS key presence and `model_fields_set` IS key
    presence, and on a body nobody serialized the two cannot disagree. They
    disagree only when this DTO's own writer materialises the absent row as a
    null. A red that a serializer change cannot satisfy would have to catch the
    reader being wrong about an input, and there is no such input.
    """

    def test_should_omit_an_untouched_title_from_the_dumped_body(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1)

        body = request.model_dump()

        # Whole-body equality, not `"title" not in body` plus per-field reads: the
        # membership form passes a body that grew a spurious extra key, and this
        # test's whole subject is which keys the body carries.
        assert body == {"content": "<p>saved</p>", "version": 1}, (
            "a title the request never carried must not appear as a key in the "
            f"dumped body, and every other field must survive it verbatim, got {body!r}"
        )

    def test_should_omit_an_untouched_title_from_the_dumped_json_body(self):
        """The JSON leg, and the one a foreign producer or consumer actually holds.

        Asserted separately rather than trusted to follow from the dict leg: in
        Pydantic v2 `model_dump_json()` does not route through the Python
        `model_dump` method, it goes to the Rust serializer. The two legs are
        separably breakable, so a green that fixed one and not the other would
        leave the shape that crosses a process boundary still saying erase.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1)

        body = json.loads(request.model_dump_json())

        assert body == {"content": "<p>saved</p>", "version": 1}, (
            "a title the request never carried must not appear as a key in the "
            f"dumped JSON body, and every other field must survive it verbatim, got {body!r}"
        )


class TestSaveDocumentRequestDtoWireShapeNegativeControl:
    """The fence around the two RED tests above -- deliberately NOT skipped.

    A serializer that dropped `title` unconditionally passes both RED tests next
    door and destroys the one intent the wire can only express WITH the key: the
    deliberate erasure. Omission must be the absent row's spelling alone.

    It lives in its own class because it PASSES at HEAD, and the marker up there
    is class-level. Parked behind that marker it would guard nothing for the whole
    duration of the red -- which is exactly the defect this scenario already named
    once and acted on, when `TestSaveDocumentRequestDtoFromALiteralBody` was kept
    live for the same reason. A fence is only a fence while it is standing.
    """

    def test_should_keep_an_explicit_null_title_in_the_dumped_body(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=None)

        body = request.model_dump()
        json_body = json.loads(request.model_dump_json())

        assert body == {"content": "<p>saved</p>", "title": None, "version": 1}, (
            f"an explicit null title must stay on the dumped body as null, got {body!r}"
        )
        assert json_body == {"content": "<p>saved</p>", "title": None, "version": 1}, (
            f"an explicit null title must stay on the JSON body as null, got {json_body!r}"
        )
