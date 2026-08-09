import pytest
from wire_shape_key_fence import assert_body_keys_track_the_model


class TestWireShapeKeyFenceReportsEveryFault:
    """The fence's own failure path, which nothing else in the suite reaches.

    `assert_body_keys_track_the_model` runs at 10 call sites across the two live
    wire-shape files -- six in `..._wire_shape_control.py`, four in
    `..._wire_shape_blank_control.py` -- and at every one of them `missing` and
    `undeclared` are both empty. So the rest of the suite exercises exactly one
    branch of it: the one that does nothing. (The three calls below are the only
    others, and they are the ones where the branch is not empty.) The collected-`faults` shape -- both faults computed before
    either is asserted, both named in one message -- was landed deliberately, on
    the grounds the control file's docstring gives for splitting its own legs: two
    sequential `assert`s abort on the first and report one broken direction where
    two may be broken. That reasoning was evidenced only by an interactive probe.
    Reverting to sequential asserts, inverting either `if`, or appending a fault
    under the wrong branch leaves all 108 tests green with the fence dead, and
    reopens at zero cost the masking the collected form exists to close.

    These tests assert the MESSAGE, not merely that it raises. "It raised" is
    satisfied by a fence that raises for the wrong reason -- a sequential-assert
    revert still raises on the both-at-once body, it just names one fault. What is
    under test here is what the message SAYS, so the both-at-once row pins that
    BOTH field names reach the one report.

    The exact equality below is load-bearing on a fact nothing declares: pytest
    does NOT rewrite asserts inside `wire_shape_key_fence.py`, because it is not
    `test_`-prefixed and nothing registers it (no `register_assert_rewrite`
    anywhere in the repo, no conftest in this directory -- both checked). Under
    rewriting the raised message gains a trailing newline and the reconstructed
    expression, measured: `"...got tail\\nassert not ['a', 'b']"`. So renaming the
    helper to a `test_`-prefixed name, adding
    `pytest.register_assert_rewrite("wire_shape_key_fence")`, or dropping a
    conftest here that does so breaks all three assertions at once, with a diff
    that reads as though the fence's wording changed when only the harness did.
    If that day comes, the fix is to compare against the message with that
    suffix -- not to loosen these to substrings, for the reason the paragraph
    above gives.

    Deliberately NOT skipped, and in its own file. Live because a marker is
    class-level and a fence parked behind one guards nothing for exactly the red
    period -- the defect this scenario has already named and acted on twice, for
    `TestSaveDocumentRequestDtoFromALiteralBody` and again for the blank-title
    control. Its own file because `..._wire_shape_control.py` is at 162 of the 200
    allowed and this is a different subject anyway: those files test what
    `SaveDocumentRequestDto` writes, this one tests the assertion helper they all
    call.
    """

    def test_should_name_a_declared_key_the_body_dropped(self):
        body = {"content": "<p>saved</p>", "version": 1}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dumped")

        assert str(failure.value) == (
            "the dumped body's key set must be exactly the model's declared fields -- "
            "['title'] was declared on the model and dropped by the serializer, "
            "got {'content': '<p>saved</p>', 'version': 1}"
        ), f"the dropped-key leg must name the dropped field, got {failure.value!s}"

    def test_should_name_a_key_the_body_carries_that_the_model_never_declared(self):
        body = {"content": "<p>saved</p>", "title": None, "version": 1, "note": "spurious"}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dumped JSON")

        assert str(failure.value) == (
            "the dumped JSON body's key set must be exactly the model's declared fields -- "
            "['note'] is on the body but declared nowhere on the model, "
            "got {'content': '<p>saved</p>', 'title': None, 'version': 1, 'note': 'spurious'}"
        ), f"the spurious-key leg must name the undeclared field, got {failure.value!s}"

    def test_should_name_both_faults_in_one_message_when_a_body_drops_and_adds_a_key(self):
        """The row the other two cannot cover, and the only reason the helper
        collects `faults` instead of asserting twice.

        A body that BOTH drops `title` and carries `note` is broken in two
        directions. Under sequential asserts the run aborts on the dropped leg and
        the report names `title` alone: a developer fixes it, re-runs, and meets
        the second fault only on the next round -- and if the dropped leg is the
        one their change fixed, the spurious key ships. Asserting only that this
        raises would pass under that revert. The equality below is what does not.
        """
        body = {"content": "<p>saved</p>", "version": 1, "note": "spurious"}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dumped")

        assert str(failure.value) == (
            "the dumped body's key set must be exactly the model's declared fields -- "
            "['title'] was declared on the model and dropped by the serializer; and "
            "['note'] is on the body but declared nowhere on the model, "
            "got {'content': '<p>saved</p>', 'version': 1, 'note': 'spurious'}"
        ), (
            "a body broken in both directions must name BOTH faults in the one message -- "
            f"got {failure.value!s}"
        )
