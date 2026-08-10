import pytest
from wire_shape_key_fence import assert_body_keys_track_the_model


class TestWireShapeKeyFenceLegGuardPreemptsTheFaultLegs:
    """The guard's ORDER, which the guard's own row cannot reach.

    `test_wire_shape_key_fence.py` already pins that a leg label outside
    `WireLeg` is refused, and by exact wording -- but it does so with a
    WELL-FORMED body, deliberately, so that the message can only have come from
    the guard. That choice is what makes the row unable to hold the property the
    guard's comment (`wire_shape_key_fence.py`, lines 100-108) argues for at
    length: with both fault legs quiet, the guard could sit ABOVE them or BELOW
    them and the observed message would be identical. Moving the guard under
    `faults` leaves all six rows of the two sibling files green (four in
    `test_wire_shape_key_fence.py`, two in the title-refusal file). Measured, not
    assumed -- the mutation is recorded in the summary that landed this file.

    "Below `faults`" means below the `assert not faults`, and the distinction is
    worth writing down because the first mutation attempt got it wrong. Moving
    the guard to sit between the `faults.append` calls and that assert is a
    NO-OP: the legs only BUILD the list there, so the guard still runs first and
    the whole suite stays green -- which reads as the row failing to bite when it
    is really the mutant failing to mutate. The order that matters is guard
    versus the RAISE, not guard versus the list.

    The property is not "the guard raises". It is that the guard raises INSTEAD
    OF the fault legs. Under the moved-guard order a broken body with a typo'd
    leg reports its fault attributed to a leg that does not exist -- a WRONG
    report, not a partial one, which is the whole reason the guard was placed
    first rather than collected into `faults` like the refusal was. So the
    fixture here is broken on the fault axis ON PURPOSE: `{"version": 1}` omits
    both `content` and `title`, arming the generic dropped leg AND the
    absent-`title` refusal at once. Two armed legs, and the exact-equality
    assertion says neither of them speaks.

    Exact equality, per both siblings' docstrings and for the same reason: a
    substring or `pytest.raises`-only pin passes under precisely the mutation
    this row exists to kill, because the moved guard still raises -- it just
    raises the other message.

    Its own file, and the seam is subject rather than line count -- though the
    cap decided the timing. The sibling that owns the guard's wording is at 172
    of the 200 allowed, so this row does not fit beside the row it extends. The
    subject is distinct in any case: the sibling files assert WHAT the fence
    says, this one asserts WHICH of two things it says when both are armed. The
    fixture omits `title`, but the expected message carries none of the
    refusal's title-specific wording and no cross-file class name -- that is the
    point of the row -- so it does not belong in the refusal file either.

    NOT skipped, and no class-level marker: the guard order is correct today, so
    a marker here would park a live mutation-killing row for a red period that
    buys nothing. Same call this scenario has now made five times.
    """

    def test_should_report_the_bad_leg_label_and_not_the_faults_of_a_broken_body(self):
        """A body broken in two directions, carried on a leg that does not exist.

        `{"version": 1}` gives `missing == {'content', 'title'}` and
        `undeclared == set()`, so both the refusal clause and the generic
        dropped clause are armed. `"dmped JSON"` is the typo the module comment
        records as MEASURED-as-accepted by mypy, which is why the run-time guard
        exists at all.

        What must come back is the leg-label message alone. Anything naming
        `'title'`, `['content']`, or `the dmped JSON body's key set` means the
        fault legs ran first and attributed a real serializer fault to a leg
        that was never declared -- sending the reader to a serializer that does
        not exist while the actual typo goes unmentioned.
        """
        body = {"version": 1}

        with pytest.raises(AssertionError) as failure:
            assert_body_keys_track_the_model(body, "dmped JSON")

        assert str(failure.value) == (
            "the leg label must be one of the declared WireLeg values, got 'dmped JSON'"
        ), (
            "a bad leg label must PREEMPT the fault legs -- a guard moved below `faults` "
            "reports a real fault attributed to a leg that does not exist, which is a "
            f"wrong report and not a partial one, got {failure.value!s}"
        )
