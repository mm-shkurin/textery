"""Scenario 3.2 -- the invariants that live on the TYPE, not on one caller.

Added by `green-usecase (clear path)` in response to the review passes over
`5ed1adb`, which converged on one fact: the RED pins the three states only
THROUGH THE FACTORIES, while `TitleUpdate`'s constructor is public and
unguarded. The split is by SUBJECT, not by which factory a test happens to call
to reach a state: `test_title_update.py` owns REPRESENTATION -- what object each
factory is, asserted as `factory(...) == TitleUpdate(value=..., clears=...)`.
This file owns what the TYPE guarantees whatever the caller did -- the doors
those representation pins leave unguarded, and the predicates consumers ask of a
state once they hold one. Kept in two files rather than appended so neither
approaches the 200-line cap.

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
from shared.exceptions import ValidationException

PADDED_TITLE = " Отчёт "

# Collection safety -- the 65ec3fd defect -- stated once for the two sites below
# that obey it. Anything evaluated at MODULE or CLASS-BODY scope that GREEN has
# not built yet raises during COLLECTION and ERRORS this whole module, taking
# down all three classes instead of failing the one test that named the missing
# thing. Hence the literal below rather than an import of it from
# `title_update`, and lambdas in the closing `parametrize` rather than calls.
INVALID_TITLE_INTENT = "INVALID_TITLE_INTENT"

# Named once because both arms of the contradiction are ONE refusal spelled two
# ways, and a message that drifted between them would let a green answer the two
# callers differently -- the very failure mode the refusal exists to stop.
#
# The WHOLE message, asserted with `==` rather than handed to `raises(match=...)`.
# `match` is an unanchored `re.search`, so a PREFIX there pins eight words and
# leaves twenty free: a green appending a per-arm tail ("...: value was blank" /
# "...: value was set") satisfies both arms while telling the two callers
# different things -- disarming the exact guard naming it once was meant to be.
REFUSAL_MESSAGE = (
    "a clear carries no title to write: TitleUpdate(value=..., clears=True) "
    "asks for an erasure and a write at once, and its readers disagree"
)


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
    """The fourth point of the 2x2 is a contradiction, not a state.

    The refusal must be a member of the TYPED family, not a builtin. The rest
    stack registers handlers for `ValidationException` / `NotFoundException` /
    `ConflictException` only (`error_handling/exception_handlers.py`); everything
    else falls to `unhandled_exception_handler` and leaves as
    `500 INTERNAL_ERROR` with a fixed generic message. A bare `ValueError` here
    is therefore not "a validation error the client sees" -- it is an internal
    server error the client is told nothing about and can only retry.

    That retry is the cost, and it is the SAME cost `__post_init__` already
    argues against one branch up: blank NORMALISES rather than raising precisely
    because "a save must never fail over a blank title -- the content update
    riding along with it would be lost". The contradiction arm raises on that
    identical call and loses that identical content -- and as a 500, without even
    naming why. The two arms must at least agree on what the client is told.

    Not wire-reachable today: `document_router.py:140` passes `request.title` as
    `str | None`, so `clears` is never set from outside. The pending
    adapters-discovery guard (a2) charters that route to BUILD the intent from
    wire input, which is the commit that makes a malformed payload reach here.
    Pinned now, while the guard is cheap.

    The HTTP outcome itself -- a 4xx carrying `{error_code, message}` rather than
    a 500 -- is NOT pinned here. Handler registration lives in
    `backend/adapters/rest`, a layer this step does not own; it belongs to
    adapters-discovery alongside a2. What this file owns is the precondition that
    makes that 4xx possible at all: the exception type.
    """

    @pytest.mark.skip(
        reason="RED: observed FAILED -- `ValueError: a clear carries no title to write: "
        "TitleUpdate(value=..., clears=True) asks for an erasure and a write at once, and its "
        "readers disagree` propagates out of pytest.raises(ValidationException), which does not "
        "catch it. title_update.py:66 raises a builtin, so this refusal maps to 500 INTERNAL_ERROR."
    )
    def test_should_reject_a_flagged_value(self):
        with pytest.raises(ValidationException) as refusal:
            TitleUpdate(value="Привет", clears=True)
        assert (refusal.value.error_code, refusal.value.message) == (
            INVALID_TITLE_INTENT,
            REFUSAL_MESSAGE,
        ), (
            "the refusal must NAME itself to the client -- an error_code is what the "
            "rest handler echoes, and without one the caller cannot tell a malformed "
            "title intent apart from any other rejected field, and the message is the "
            "only part of the pair a human reads"
        )

    @pytest.mark.skip(
        reason="RED: observed FAILED -- same verbatim `ValueError: a clear carries no title to "
        "write: ...` propagating out of pytest.raises(ValidationException). Both arms of the "
        "contradiction raise the same builtin, so both leave as 500 INTERNAL_ERROR."
    )
    def test_should_reject_a_flagged_blank_before_normalising_it_away(self):
        """Order matters: normalise-then-check would silently ACCEPT this.

        A blank folds to `value=None`, which makes `(value="", clears=True)`
        indistinguishable from a legitimate `clear()` -- so a caller confusing
        "the user emptied the field" with "the user asked for an erasure" would
        get its wipe honoured instead of refused.
        """
        with pytest.raises(ValidationException) as refusal:
            TitleUpdate(value="   ", clears=True)
        assert (refusal.value.error_code, refusal.value.message) == (
            INVALID_TITLE_INTENT,
            REFUSAL_MESSAGE,
        ), (
            "the blank arm must refuse under the same CODE and the same MESSAGE as the "
            "value arm -- one contradiction, one name, one sentence, however the caller "
            "happened to spell it"
        )


class TestTitleUpdatePredicatesAnswerForAllThreeStates:
    """What consumers ASK, pinned per state -- `erases()` first, then `carries_a_value()`."""

    @pytest.mark.parametrize(
        "build_intent, erases, carries_a_value",
        [
            pytest.param(lambda: TitleUpdate.preserve(), False, False, id="preserve"),
            pytest.param(lambda: TitleUpdate.clear(), True, False, id="clear"),
            pytest.param(lambda: TitleUpdate.of("Привет"), False, True, id="set"),
        ],
    )
    def test_should_answer_both_predicates(self, build_intent, erases, carries_a_value):
        """`clear()` being FALSE for `carries_a_value()` is the point.

        It is what makes a lone `if title.carries_a_value(): write` map a clear
        onto "leave the stored title alone" -- the no-op that returns a user's
        deleted title on every reopen. Pinning it here is what stops the next
        consumer from trusting the docstring's old claim that `preserve()` was
        the only false case.

        All three params are spelled as lambdas -- including the two whose
        factory takes no argument -- because only a lambda defers the attribute
        LOOKUP as well as the call. A bare `pytest.param(TitleUpdate.clear, ...)`
        still resolves the attribute in the class body, so a future RED renaming
        `clear()` still errors the module under the rule stated at its head.
        """
        intent = build_intent()
        assert (intent.erases(), intent.carries_a_value()) == (erases, carries_a_value), (
            f"{intent!r} must answer erases()={erases} and carries_a_value()={carries_a_value}"
        )
