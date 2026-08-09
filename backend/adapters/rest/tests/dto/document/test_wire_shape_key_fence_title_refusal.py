import pytest
from wire_shape_key_fence import assert_body_keys_track_the_model


class TestWireShapeKeyFenceRefusesTheAbsentTitleRow:
    """The `missing` leg's absent-`title` partition, split out of
    `test_wire_shape_key_fence.py` so its skip marker could sit at CLASS level.

    Green as of 2.1's green, and the marker is gone -- but the split it forced
    stays, for the reason below and the subject seam below that.

    Co-located, the marker would have had to be METHOD-level: a class marker would
    have taken that file's passing rows with it, and they are the only thing in the
    suite that reaches the fence's failure path at all. Parking them for the whole
    red period is the trap this scenario has already sprung three times. The split
    dissolved the conflict rather than trading one hazard for the other -- the
    marker sat at class level, matching both siblings and the tech binding, with no
    live row behind it.

    The seam is subject, not line count. The other file's rows are model-agnostic:
    the fence reports faults in both directions and names both in one message. This
    row is specific to scenario 2.1 and to one field. It is also the only row whose
    expected message names a sibling class and file, so that cross-file coupling now
    lives in the file whose whole subject is that relationship.
    """

    def test_should_refuse_the_untouched_row_rather_than_call_its_absent_title_a_dropped_field(
        self,
    ):
        """The row the charter calls the guard, and why it is ONE mechanism, not two.

        `assert "title" in body` layered on top of the `missing` leg would fire on
        exactly the bodies that leg already fires on, because the fence's only
        observable is `body` and the untouched row is INDISTINGUISHABLE from a
        serializer that dropped `title`: both are the same dict, with the same
        keys, and the thing that separates them -- which call site produced it --
        is not visible from in here. Two mechanisms on one trigger is the same
        assertion wearing two names, and the second would only ever preempt the
        first.

        What IS distinguishable is WHICH field is absent. `title` is the single
        declared field whose absence is under active dispute: the skipped class in
        `test_save_document_request_dto_wire_shape.py` asserts the untouched row
        must omit it, and green for 2.1 makes that the emitted shape. No row
        anywhere claims a body may omit `content` or `version`, so their absence
        stays an unambiguous serializer fault -- which is what the first row of
        `test_wire_shape_key_fence.py` now pins. So the `missing` leg is
        PARTITIONED, not doubled: `title` gets a refusal that names the class the
        fence must not be called from, every other declared field keeps the generic
        wording.

        The refusal is a fault like any other, collected into `faults` rather than
        raised ahead of them, so a body that is both absent-`title` AND carrying a
        spurious key still reports both directions in the one message -- the shape
        the both-faults row next door exists to hold.

        The expected message names `TestSaveDocumentRequestDtoWireShape` and its
        file. Both are asserted against the FENCE's string, not against the real
        class, so a rename leaves this row green while the message points at
        nothing. That is the known cost of naming the forbidden call site at all,
        and it is the right trade: a refusal that does not say where the body came
        from leaves the reader with the same puzzle the generic fault already left
        them. Exact equality stays -- a substring pin does not kill a mutation that
        mangles the `'; and '` joiner or drops the `got {body!r}` tail, which is the
        finding a prior unit landed and this row inherits.
        """
        body = {"content": "<p>saved</p>", "version": 1}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dumped")

        assert str(failure.value) == (
            "the dumped body's key set must be exactly the model's declared fields -- "
            "'title' is absent, which this fence cannot judge: absence is the CORRECT "
            "shape for a title-untouched save (TestSaveDocumentRequestDtoWireShape in "
            "test_save_document_request_dto_wire_shape.py) and a serializer fault "
            "everywhere else, and the body alone does not say which -- do not call this "
            "fence on the untouched row, "
            "got {'content': '<p>saved</p>', 'version': 1}"
        ), (
            "an absent `title` must be REFUSED by name, not reported as a dropped field -- "
            f"calling it dropped asks green to emit the erasure, got {failure.value!s}"
        )
