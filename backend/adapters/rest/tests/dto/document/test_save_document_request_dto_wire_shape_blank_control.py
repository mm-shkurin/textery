import json

from wire_shape_key_fence import assert_body_keys_track_the_model

from dto.document.document_dtos import SaveDocumentRequestDto


class TestSaveDocumentRequestDtoWireShapeBlankTitleControl:
    """Story 17's rows 3 and 4: a BLANK title on the wire means PRESERVE, not erase.

    A third live file in the wire-shape set, split off
    `test_save_document_request_dto_wire_shape_control.py` at the 200-line cap
    rather than by trimming anything there. Live for the same reason that file
    is live: the marker next door is class-level, so a fence parked behind it
    guards nothing for exactly the red period, which is when the green that
    could trip it gets written.

    These rows were the hole the rest of the set left open. Across the whole
    pair `title` was only ever constructed absent, `None`, or `" Отчёт "` --
    `""` and `"   "` appeared nowhere but the RED class's prose table. Row 4
    pins that a NON-BLANK title survives, so a serializer that rewrites only
    BLANK titles is the identity on every asserted row and passes the entire
    suite. Measured at HEAD on pydantic 2.13.4: a `field_serializer("title")`
    spelled `if v is not None and not v.strip(): return None` -- the most
    natural line a developer writes -- passed all 102 rest tests.

    What that green does is not cosmetic. On the wire it emits `"title": null`,
    and HEAD's reader (`document_dtos.py:57`) maps null to
    `TitleUpdate.clear()`. So a row the ADR documents as PRESERVE arrives at the
    usecase as an ERASURE, and the user's title is wiped by a request that asked
    for nothing of the kind. The blank-vs-null distinction is the load-bearing
    one on this DTO, and it is the writer side of it that was unpinned.

    The earlier dismissal -- "a blank is absorbed by the domain's blank fold in
    `TitleUpdate.of()`" -- does not cover this. That is reader-side reasoning
    about a writer-side gap: the fold only runs on the `of()` branch, and a
    blank rewritten to null never reaches `of()` at all. It holds in the
    blank->of direction and fails in the blank->null one.

    Both legs per value, because `model_dump_json()` does not route through the
    Python `model_dump` in Pydantic v2 -- it goes to the Rust serializer, and
    JSON is the leg a foreign consumer actually holds.
    """

    def test_should_keep_an_empty_title_on_the_dumped_body_verbatim(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title="")

        body = request.model_dump()

        assert body == {"content": "<p>saved</p>", "title": "", "version": 1}, (
            "an empty-string title must stay on the dumped body as an empty string -- "
            f"rewriting it to null turns a documented preserve into an erasure, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped")

    def test_should_keep_an_empty_title_on_the_dumped_json_body_verbatim(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title="")

        body = json.loads(request.model_dump_json())

        assert body == {"content": "<p>saved</p>", "title": "", "version": 1}, (
            "an empty-string title must stay on the JSON body as an empty string -- "
            f"rewriting it to null turns a documented preserve into an erasure, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped JSON")

    def test_should_keep_a_whitespace_only_title_on_the_dumped_body_verbatim(self):
        """The row `""` cannot cover: a whitespace-only title is falsy under
        `.strip()` but not under a bare truth test, so the two blanks are reached
        by different damaging spellings and neither implies the other.
        """
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title="   ")

        body = request.model_dump()

        assert body == {"content": "<p>saved</p>", "title": "   ", "version": 1}, (
            "a whitespace-only title must reach the dumped body byte for byte -- neither "
            f"stripped to empty nor rewritten to null, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped")

    def test_should_keep_a_whitespace_only_title_on_the_dumped_json_body_verbatim(self):
        request = SaveDocumentRequestDto(content="<p>saved</p>", version=1, title="   ")

        body = json.loads(request.model_dump_json())

        assert body == {"content": "<p>saved</p>", "title": "   ", "version": 1}, (
            "a whitespace-only title must reach the JSON body byte for byte -- neither "
            f"stripped to empty nor rewritten to null, got {body!r}"
        )
        assert_body_keys_track_the_model(body, "dumped JSON")
