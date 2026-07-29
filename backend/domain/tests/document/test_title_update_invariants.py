"""Scenario 3.2 -- the invariants that live on the TYPE, not on one caller.

Added by `green-usecase (clear path)` in response to the review passes over
`5ed1adb`, which converged on one fact: the RED pins the three states only
THROUGH THE FACTORIES, while `TitleUpdate`'s constructor is public and
unguarded. `test_title_update.py` owns the factory-level pins; this file owns
the doors those pins leave open. Kept separate rather than appended so neither
file approaches the 200-line cap.

Three findings, three classes:

1.  Moving the blank rule into `of()` retires the only live blank guard
    (`SaveDocument._title_intent`'s `is_blank()` branch, deleted by this green as
    vacuous) and replaces it with nothing on the CONSTRUCTOR path. A rest route
    mapping a Pydantic field to `TitleUpdate(value="")` instead of `of("")`
    reaches the CAS and writes `SET title = ''` over a stored title. Pinned
    through the constructor, which is the door.

2.  `TitleUpdate(value="x", clears=True)` was representable and its two readers
    resolve it OPPOSITELY -- the db CAS writes `"x"` and ignores the flag; a
    clears-first reader nulls the column and discards `"x"`. Which consumer read
    it decided the user's data. Pinned as unconstructible.

3.  `carries_a_value()` had NO test anywhere and its contract INVERTED under this
    green: its docstring said `preserve()` was the only false case, but `clear()`
    is also `value=None`. Both consumers then omit the title column and the clear
    silently no-ops. Pinned across all three states, alongside the behavioural
    `erases()` that exists so consumers stop reading the raw `clears` field.
"""

import pytest

from document.title_update import TitleUpdate

PADDED_TITLE = " Отчёт "


class TestTitleUpdateClosesTheConstructorDoor:
    """The blank rule is an invariant of the type, not of `of()`."""

    @pytest.mark.parametrize("raw", ["", "   ", "\t\n"], ids=["empty", "spaces", "control"])
    def test_should_normalise_a_blank_built_through_the_constructor(self, raw):
        assert TitleUpdate(value=raw) == TitleUpdate(value=None, clears=False), (
            f"TitleUpdate(value={raw!r}) built directly -- bypassing of() -- must still "
            f"carry no title intent, or a caller that skips the factory writes SET title = ''"
        )

    def test_should_keep_a_padded_real_title_whole_through_the_constructor(self):
        """The same tripwire as the factory's, restated on the door beside it.

        A `__post_init__` fixing blankness with `value.strip() or None` passes
        every blank case above and trims every legitimate title as a side effect
        -- the exact rewrite the ADR rejects.
        """
        assert TitleUpdate(value=PADDED_TITLE) == TitleUpdate(value=PADDED_TITLE, clears=False), (
            "blankness is TESTED, never applied -- a real title keeps its padding"
        )


class TestTitleUpdateRefusesToCarryAValueAndAClearAtOnce:
    """The fourth point of the 2x2 is a contradiction, not a state."""

    def test_should_reject_a_flagged_value(self):
        with pytest.raises(ValueError, match="a clear carries no title to write"):
            TitleUpdate(value="Привет", clears=True)

    def test_should_reject_a_flagged_blank_before_normalising_it_away(self):
        """Order matters: normalise-then-check would silently ACCEPT this.

        A blank folds to `value=None`, which makes `(value="", clears=True)`
        indistinguishable from a legitimate `clear()` -- so a caller confusing
        "the user emptied the field" with "the user asked for an erasure" would
        get its wipe honoured instead of refused.
        """
        with pytest.raises(ValueError, match="a clear carries no title to write"):
            TitleUpdate(value="   ", clears=True)


class TestTitleUpdatePredicatesAnswerForAllThreeStates:
    """What consumers ASK, pinned per state -- `erases()` first, then `carries_a_value()`."""

    @pytest.mark.parametrize(
        "intent, erases, carries_a_value",
        [
            pytest.param(TitleUpdate.preserve(), False, False, id="preserve"),
            pytest.param(TitleUpdate.clear(), True, False, id="clear"),
            pytest.param(TitleUpdate.of("Привет"), False, True, id="set"),
        ],
    )
    def test_should_answer_both_predicates(self, intent, erases, carries_a_value):
        """`clear()` being FALSE for `carries_a_value()` is the point.

        It is what makes a lone `if title.carries_a_value(): write` map a clear
        onto "leave the stored title alone" -- the no-op that returns a user's
        deleted title on every reopen. Pinning it here is what stops the next
        consumer from trusting the docstring's old claim that `preserve()` was
        the only false case.
        """
        assert (intent.erases(), intent.carries_a_value()) == (erases, carries_a_value), (
            f"{intent!r} must answer erases()={erases} and "
            f"carries_a_value()={carries_a_value}"
        )
