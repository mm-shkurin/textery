import pytest
from wire_shape_key_fence import assert_body_keys_track_the_model


class TestWireShapeKeyFenceReportsEveryFault:
    """The fence's own failure path, which nothing else in the suite reaches.

    `assert_body_keys_track_the_model` runs at 10 call sites across the two live
    wire-shape files -- six in `..._wire_shape_control.py`, four in
    `..._wire_shape_blank_control.py` -- and at every one of them `missing` and
    `undeclared` are both empty. So the rest of the suite exercises exactly one
    branch of it: the one that does nothing. (The four calls below, plus the two
    in `test_wire_shape_key_fence_title_refusal.py`, are the only others, and
    they are the ones where the branch is not empty.)

    The `['content']`-as-missing literals in the first and third rows replaced
    `['title']` ones, which read as a contract stating that `title: null` is the
    well-formed body and an absent `title` is the fault -- scenario 2.1's
    invariant exactly inverted. The absent-`title` body is now the subject of
    `test_wire_shape_key_fence_title_refusal.py`, where it is REFUSED rather than
    certified -- the third row in THIS file is the leg-label guard -- and `content` is the
    honest fixture for the generic leg because nothing anywhere claims a body may
    omit it. Those literals are no longer PROVISIONAL in that direction; they stay
    coupled to the declared set, which is the next unit's row.

    The collected-`faults` shape -- both faults computed before
    either is asserted, both named in one message -- was landed deliberately, on
    the grounds the control file's docstring gives for splitting its own legs: two
    sequential `assert`s abort on the first and report one broken direction where
    two may be broken. That reasoning was evidenced only by an interactive probe.
    Reverting to sequential asserts, inverting either `if`, or appending a fault
    under the wrong branch left all 108 tests of the suite AS IT STOOD THEN green
    with the fence dead -- a measurement taken before this class existed, hence the
    stale count; it is recorded as history, not as a claim about the suite today.
    It reopens at zero cost the masking the collected form exists to close.

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

    The CLASS is deliberately NOT skipped, and in its own file. Every row here is
    live, because a marker is class-level by default and a fence parked behind one
    guards nothing for exactly the red period -- the defect this scenario has
    already named and acted on three times, for
    `TestSaveDocumentRequestDtoFromALiteralBody`, for the negative control, and
    again for the blank-title control. Its own file because
    `..._wire_shape_control.py` is at 170 of the 200 allowed and this is a
    different subject anyway: those files test what
    `SaveDocumentRequestDto` writes, this one tests the assertion helper they all
    call.

    Scenario 2.1's row -- the absent-`title` body the fence must REFUSE rather
    than call a dropped field -- lives in
    `test_wire_shape_key_fence_title_refusal.py`, split out while it was RED so its
    skip marker could sit at CLASS level without taking the rows here with it. That
    row is green as of 2.1's green and its marker is gone; the split stays, because
    the seam it drew is by subject. This file stays model-agnostic: fault reporting
    in both directions, both named in one message.
    """

    def test_should_name_a_declared_key_the_body_dropped(self):
        """The dropped field is `content`, NOT `title`, and the swap is the point.

        This row shipped with a body that dropped `title`, which read as a
        contract saying `title: null` is the well-formed shape and an absent
        `title` is the fault -- the invariant of scenario 2.1 exactly inverted.
        `content` carries no such dispute: no row anywhere claims a body may
        omit it, so its absence is unambiguously a serializer fault and this
        row's subject is the generic leg alone. The absent-`title` body is now
        the subject of its own file, `test_wire_shape_key_fence_title_refusal.py`,
        whose rows REFUSE it rather than certify it.

        Re-fixtured, not loosened: exact equality survives, for the reason the
        class docstring gives.
        """
        body = {"title": None, "version": 1}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dumped")

        assert str(failure.value) == (
            "the dumped body's key set must be exactly the model's declared fields -- "
            "['content'] was declared on the model and dropped by the serializer, "
            "got {'title': None, 'version': 1}"
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

    def test_should_refuse_a_leg_label_that_is_not_a_declared_wire_leg(self):
        """The guard nothing stood behind, on the exact typo that was measured.

        `"dmped JSON"` is not a hypothetical: the module comment records it as
        MEASURED-as-accepted by mypy, which is why the run-time guard exists. That
        measurement never became a test, and `/refactor` then rewrote the guard's
        accepted set to `get_args(WireLeg)` with nothing pinning either the set or
        the wording. The label is interpolation-only, so a wrong one is invisible to
        every other row here -- deleting the guard leaves them all green.

        The body is WELL-FORMED, deliberately: with both fault legs quiet the
        message can only come from the guard, and the exact equality kills a revert
        that keeps raising but drops the offending label from the text. It does NOT
        pin the guard's PREEMPTION -- with no fault to preempt, moving the guard
        below `faults` leaves this row green. That coverage is a separate chartered
        step; do not read this row as having closed it.
        """
        body = {"content": "<p>saved</p>", "title": None, "version": 1}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dmped JSON")

        assert str(failure.value) == (
            "the leg label must be one of the declared WireLeg values, got 'dmped JSON'"
        ), (
            "a leg label outside WireLeg must be refused by name -- an unpinned guard is "
            f"deletable without a red row, got {failure.value!s}"
        )

    def test_should_name_both_faults_in_one_message_when_a_body_drops_and_adds_a_key(self):
        """The row the other two cannot cover, and the only reason the helper
        collects `faults` instead of asserting twice.

        A body that BOTH drops `content` and carries `note` is broken in two
        directions. Under sequential asserts the run aborts on the dropped leg and
        the report names `content` alone: a developer fixes it, re-runs, and meets
        the second fault only on the next round -- and if the dropped leg is the
        one their change fixed, the spurious key ships. Asserting only that this
        raises would pass under that revert. The equality below is what does not.

        The dropped field is `content` for the reason the first row gives: a
        body dropping `title` is the untouched row's CORRECT shape, and pinning
        it here as a fault states the inverted invariant.
        """
        body = {"title": None, "version": 1, "note": "spurious"}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dumped")

        assert str(failure.value) == (
            "the dumped body's key set must be exactly the model's declared fields -- "
            "['content'] was declared on the model and dropped by the serializer; and "
            "['note'] is on the body but declared nowhere on the model, "
            "got {'title': None, 'version': 1, 'note': 'spurious'}"
        ), (
            "a body broken in both directions must name BOTH faults in the one message -- "
            f"got {failure.value!s}"
        )
