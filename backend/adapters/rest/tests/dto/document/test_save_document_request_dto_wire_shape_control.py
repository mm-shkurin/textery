import json

from dto.document.document_dtos import SaveDocumentRequestDto


def _assert_body_keys_track_the_model(request: SaveDocumentRequestDto, body: dict, leg: str):
    """The half of the shape that whole-body equality against a literal cannot hold.

    Equality with a frozen dict is asymmetric under extension. It catches a
    SPURIOUS key -- that is why it was chosen -- but it cannot catch a DROPPED
    declared one: the day a later scenario adds a field to
    `SaveDocumentRequestDto`, a green whose serializer hand-builds its dict (a
    non-`wrap` `@model_serializer` returning `{"content": ..., "version": ...}`)
    silently omits the new field, and every `body == {...}` in this file still
    holds, because the literal was frozen beside the old model. These two
    assertions read `model_fields_set` / `model_fields` at run time, so they grow
    with the model instead of freezing next to it.

    A WEAKER pin than those literals, not a stronger one: it reads the model's
    own bookkeeping off the object under test, so a serializer wrong in the same
    direction agrees with itself -- the private-encoding structure the RED class
    in `test_save_document_request_dto_wire_shape.py` rejects, on the key axis.
    On the CURRENT model it catches nothing the literals miss. It is here for
    what they provably cannot cover, not because it is a better assertion.

    Called only from this LIVE class: the same hole exists in the skipped RED
    class next door, but a call there would be dark for exactly the red period,
    which is when the green that could trip it gets written.
    """
    declared = set(SaveDocumentRequestDto.model_fields)
    missing = request.model_fields_set - body.keys()
    assert not missing, (
        f"every field the request actually carries must appear in the {leg} body -- "
        f"{sorted(missing)} was declared on the model, set on this request, and dropped "
        f"by the serializer, got {body!r}"
    )
    undeclared = body.keys() - declared
    assert not undeclared, (
        f"the {leg} body must carry no key outside the model's declared fields, "
        f"got {sorted(undeclared)} in {body!r}"
    )


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
    growing a row at a time as story 17's wire table gets pinned. They share only
    the import, so the seam is clean.
    """

    def test_should_keep_an_explicit_null_title_in_the_dumped_body(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=None)

        body = request.model_dump()

        assert body == {"content": "<p>saved</p>", "title": None, "version": 1}, (
            f"an explicit null title must stay on the dumped body as null, got {body!r}"
        )
        _assert_body_keys_track_the_model(request, body, "dumped")

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
        _assert_body_keys_track_the_model(request, body, "dumped JSON")

    def test_should_keep_a_real_title_on_the_dumped_body_byte_for_byte(self):
        """Story 17's row 4: a real title is stored VERBATIM, padding included.

        The other rows in this pair carry an absent or a null title, so every
        value-rewriting serializer is the identity on all of them. A `mode="wrap"`
        green that omits the absent row and `.strip()`s the rest passed all six
        tests here while sending `" Отчёт "` out as `"Отчёт"` -- the DTO's own
        docstring (`document_dtos.py:53`, "no `.strip()`") and the ADR's row 4
        both violated, with nothing red. This is the row that carries actual user
        data, and it was the only one nothing pinned on the writer side.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title=" Отчёт ")

        body = request.model_dump()

        assert body == {"content": "<p>saved</p>", "title": " Отчёт ", "version": 1}, (
            "a real title must reach the body byte for byte, padding included, "
            f"got {body!r}"
        )
        _assert_body_keys_track_the_model(request, body, "dumped")

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
        _assert_body_keys_track_the_model(request, body, "dumped JSON")
