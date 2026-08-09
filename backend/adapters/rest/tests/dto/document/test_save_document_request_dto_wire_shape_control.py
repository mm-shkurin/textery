import json

from wire_shape_key_fence import assert_body_keys_track_the_model

from dto.document.document_dtos import SaveDocumentRequestDto


class TestSaveDocumentRequestDtoWireShapeNegativeControl:
    """The fence around the RED tests in `test_save_document_request_dto_wire_shape.py`.

    Deliberately NOT skipped, and deliberately in its own FILE. Read it beside
    that one: the two are a pair, and this half exists to forbid the greens that
    would over-satisfy the other.

    A serializer that dropped `title` unconditionally passes both RED tests there
    and destroys the one intent the wire can only express WITH the key: the
    deliberate erasure. Omission must be the absent row's spelling alone.

    It is unskipped because it PASSES at HEAD and the marker over there is
    class-level. Parked behind that marker it would guard nothing for the whole
    duration of the red -- exactly the defect this scenario already named once and
    acted on, when `TestSaveDocumentRequestDtoFromALiteralBody` was kept live for
    the same reason. A fence is only a fence while it is standing.

    It is a separate file because the pair reached the 200-line cap: at the cap a
    file cannot absorb so much as a clarifying line, and both halves are still
    growing a row at a time as story 17's wire table gets pinned. The blank-title
    rows -- the ones whose damaging green turns a PRESERVE into an ERASURE -- have
    since split off again into
    `test_save_document_request_dto_wire_shape_blank_control.py` for the same
    reason, and the key-tracking assertion both live classes call now lives in
    `wire_shape_key_fence.py`. The seams are clean: every file shares only
    imports.
    """

    def test_should_keep_an_explicit_null_title_in_the_dumped_body(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=None)

        body = request.model_dump()

        assert body == {"content": "<p>saved</p>", "title": None, "version": 1}, (
            f"an explicit null title must stay on the dumped body as null, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped")

    def test_should_keep_an_explicit_null_title_in_the_dumped_json_body(self):
        """The JSON leg of the fence, split off its dict leg.

        The two were one method, which meant a dict-leg regression aborted before
        the JSON assertion ever ran and the report named one broken leg where two
        may be broken. The RED class next door splits its own legs on exactly the
        grounds that Python `model_dump` and the Rust JSON serializer are
        separably breakable; the fence contradicted its neighbour for no reason.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=None)

        body = json.loads(request.model_dump_json())

        assert body == {"content": "<p>saved</p>", "title": None, "version": 1}, (
            f"an explicit null title must stay on the JSON body as null, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped JSON")

    def test_should_keep_a_real_title_on_the_dumped_body_byte_for_byte(self):
        """Story 17's row 4: a real title is stored VERBATIM, padding included.

        The other rows in this pair carry an absent or a null title, so every
        value-rewriting serializer is the identity on all of them. A `mode="wrap"`
        green that omits the absent row and `.strip()`s the rest passed all six
        tests here while sending `" Отчёт "` out as `"Отчёт"` -- the DTO's own
        docstring (`document_dtos.py:53`, "no `.strip()`") and the ADR's row 4
        both violated, with nothing red. This is the row that carries actual user
        data, and it was the only one nothing pinned on the writer side.

        It is also the call site the key fence was written for. Every other row
        here constructs a SUBSET-shaped request by intent -- the absent row omits
        `title`, and that omission is the subject of the RED class -- whereas this
        one sets all three declared fields, so the fence has the full declared set
        to drop from and its key leg runs against a body that is supposed to carry
        everything. Whole-body equality is asserted alongside the fence rather than
        delegated to it, for the reason the fence's own docstring gives: it reads
        `model_fields` off the class under test, and a serializer wrong in the same
        direction agrees with itself.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=" Отчёт ")

        body = request.model_dump()

        assert body == {"content": "<p>saved</p>", "title": " Отчёт ", "version": 1}, (
            "a real title must reach the body byte for byte, padding included, "
            f"got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped")

    def test_should_keep_a_real_title_on_the_dumped_json_body_byte_for_byte(self):
        """The JSON leg of row 4, asserted separately for the Rust-serializer
        reason this pair already argues for the absent row: `model_dump_json()`
        does not route through the Python `model_dump`, so a green could trim on
        one leg and not the other -- and this is the leg a foreign consumer holds.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=" Отчёт ")

        body = json.loads(request.model_dump_json())

        assert body == {"content": "<p>saved</p>", "title": " Отчёт ", "version": 1}, (
            "a real title must reach the JSON body byte for byte, padding included, "
            f"got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped JSON")

    def test_should_keep_hostile_content_on_the_dumped_body_byte_for_byte(self):
        """`content` is the largest user-data surface here, and it was unpinned.

        Across this pair and the round-trip file `content` was only ever
        `"<p>saved</p>"` or `'c'`: ASCII, single-line, no surrounding whitespace.
        A `mode="wrap"` serializer normalizing whitespace on `content` alone --
        the exact shape measured against for `title` one row over -- is the
        identity on every one of those values and ships entirely green. Measured
        at HEAD: a `field_serializer("content")` doing `" ".join(v.split())`
        passed all 102 rest tests. This row is the one it cannot pass. The
        leading and trailing spaces, the blank line, and the non-ASCII body are
        written out at the assertion site rather than shared with the arrange
        side through a constant -- an equality against a constant both sides read
        is satisfied by any serializer, because it compares the value to itself.

        `title` is set EXPLICITLY to null rather than left absent, so this row's
        subject stays `content` alone: an absent title is the one key whose
        presence is under active dispute in the RED class next door, and a
        content row whose expected body depended on that dispute would flip from
        fence to red the moment the green lands. Explicit null is stable across it.
        """
        request = SaveDocumentRequestDto(
            content="  <p>Отчёт\n\n  за май</p>  ", version=1, title=None
        )

        body = request.model_dump()

        assert body == {"content": "  <p>Отчёт\n\n  за май</p>  ", "title": None, "version": 1}, (
            "content must reach the body byte for byte -- surrounding whitespace, interior "
            f"newlines and non-ASCII text all verbatim, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped")

    def test_should_keep_hostile_content_on_the_dumped_json_body_byte_for_byte(self):
        """The JSON leg of the content row, and the one that actually crosses a
        process boundary. Asserted separately for the reason this pair argues at
        every other row: `model_dump_json()` does not route through the Python
        `model_dump` in Pydantic v2, it goes to the Rust serializer, so a green
        could normalize on one leg and not the other. `title` is explicit null
        here for the reason the dict leg gives.
        """
        request = SaveDocumentRequestDto(
            content="  <p>Отчёт\n\n  за май</p>  ", version=1, title=None
        )

        body = json.loads(request.model_dump_json())

        assert body == {"content": "  <p>Отчёт\n\n  за май</p>  ", "title": None, "version": 1}, (
            "content must reach the JSON body byte for byte -- surrounding whitespace, "
            f"interior newlines and non-ASCII text all verbatim, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped JSON")
