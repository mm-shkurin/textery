"""Scenario 3.2 -- the refusal a CLIENT reads carries no internal shape.

Inserted by the coverage pass over `e44e069`. Its sibling
`test_title_update_invariants.py` pins the refusal's message with `==` against a
test-local literal, which is a DRIFT detector: delete one period and it fails.
What it cannot see is a COORDINATED edit -- a green that rewrites the sentence
AND updates the `REFUSAL_MESSAGE` literal beside it in one stroke stays green
whatever the new sentence contains. That is not a hypothetical shape of change;
it is exactly what "make the error message more helpful" looks like, and the
most helpful thing to paste in is `_CONTRADICTION_DETAIL` -- the developer
sentence that was deliberately taken OFF the wire, naming a domain class and its
constructor signature (`TitleUpdate(value=..., clears=True)`).

So this file pins the PROPERTY instead of the bytes, and the two guards are
ORTHOGONAL by construction: the `==` pin rules out every message except one, and
survives any rewrite; this one rules out a FAMILY of messages, and survives every
rewrite. Neither subsumes the other, and only the pair is closed under a
coordinated edit.

Both assertions read the message off a LIVE RAISED EXCEPTION, never off the
constant. Asserting the property on `INVALID_TITLE_INTENT_MESSAGE` alone would
leave the raise free to pass a different string entirely, and would pin the
safety of a constant rather than the safety of what a client actually receives.

The production constant IS imported here, unlike the literal in the sibling
file, and for the same reason that made the literal right there: an imported
constant makes an EQUALITY assertion tautological, but a PROPERTY assertion over
it is not -- the claim is about whatever the symbol holds, and the whole point is
that it must hold under any future edit. Re-typing the sentence here would put
the guard back on bytes.

ALREADY-GREEN REGRESSION GUARD. The current message,
"A title cannot be set and cleared at the same time.", satisfies both properties
today, so this file is expected to PASS on unmutated production -- the precedent
for landing such a guard live and unskipped is `red-adapter db (TitleUpdate
unwrap)` and `red-usecase (the raw-str arm of _title_intent)`. It is verified
against a kill-mutant rather than only against a green run, so that it is not
mistaken for a test that would pass over an empty message too.
"""

import pytest

from document.title_update import _CONTRADICTION_DETAIL, TitleUpdate
from shared.exceptions import ValidationException

# The value that, paired with a clear, IS the refusal -- spelled once. A plain
# `str` is safe to bind at module scope, the same as the siblings' `PADDED_TITLE`.
# What must NOT reach module or class-body scope is the CONSTRUCTION below that
# uses it: constructing it raises, and a raise during COLLECTION errors the whole
# module instead of failing one test -- the 65ec3fd defect the sibling files state
# at their heads. Hence the helper, whose body runs inside each test.
FLAGGED_VALUE = "Привет"


def refuse_a_flagged_value() -> ValidationException:
    """The one call under test, so neither test below re-spells the raise.

    A helper rather than a fixture: it must run INSIDE the assertion's test so
    that a green which stops raising fails these tests rather than erroring them.
    """
    with pytest.raises(ValidationException) as refusal:
        TitleUpdate(value=FLAGGED_VALUE, clears=True)
    return refusal.value


class TestTitleUpdateRefusalIsSafeToShowAClient:
    """`validation_exception_handler` echoes `exc.message` VERBATIM.

    It is the only handler in `error_handling/exception_handlers.py` that does --
    404, 409 and 500 all substitute a fixed constant, and that file's own comment
    says why: echoing `str(exc)` "would put an internal id shape in the response,
    which Security 5.1 names explicitly as a leak". So the message raised here is
    not a developer diagnostic that happens to be readable; it is response body
    text, and it is the ONLY `ValidationException` in the tree whose message was
    ever a 30-word internal sentence.
    """

    @pytest.mark.parametrize(
        "forbidden",
        [
            pytest.param("(", id="call-or-constructor-syntax"),
            pytest.param("=", id="keyword-argument-syntax"),
            pytest.param(TitleUpdate.__name__, id="domain-class-name"),
        ],
    )
    def test_should_not_show_a_client_any_internal_shape(self, forbidden):
        """Three fragments, each the signature of a distinct leak.

        `(` and `=` together are what makes a sentence read as SOURCE -- every
        internal shape this message could grow (`TitleUpdate(value=..., clears=
        True)`, a repr, a field list) needs at least one of them, and neither has
        any business in a sentence written for a human. The class name is the
        third independently: a message could name `TitleUpdate` in prose, with no
        punctuation at all, and still tell a client what our domain types are
        called.

        Spelled as `TitleUpdate.__name__` rather than the string "TitleUpdate":
        the guard is about the class this refusal belongs to, so a rename must
        carry it along rather than silently retire it.

        The non-blank guard below is the HAYSTACK half of the vacuity argument
        that the sibling test makes for the needle. Three fragments that can
        never be empty still assert nothing against an empty message: `"(" not
        in ""` is True, so a green that blanked `INVALID_TITLE_INTENT_MESSAGE`
        passes all three params. Nor does the `==` drift pin cover it -- that pin
        compares against a test-LOCAL literal, so the coordinated edit this file
        exists to catch blanks both sides at once and stays green. `.strip()`
        rather than `!= ""`: an all-whitespace message is equally vacuous, and
        equally useless to the client reading it.
        """
        message = refuse_a_flagged_value().message
        assert message.strip() != "", (
            "the refusal must carry actual text -- a blank message makes every "
            "'this fragment is not on the wire' assertion below vacuously true, "
            "and hands the client a 4xx that says nothing"
        )
        assert forbidden not in message, (
            f"the client-facing refusal must not contain {forbidden!r} -- "
            f"`validation_exception_handler` echoes this message verbatim into the "
            f"response body, so source syntax or a domain class name in it is a "
            f"leak (Security 5.1), not merely untidy prose"
        )

    def test_should_keep_the_developer_detail_off_the_client_message(self):
        """The specific text the properties above exist to keep out.

        `_CONTRADICTION_DETAIL` is the sentence the constructor USED to raise, and
        the one a future "more helpful message" edit would reach for first. Named
        here directly so the guard does not rest on the three fragments happening
        to cover it.

        Its non-emptiness is asserted in the same breath, and not as a
        formality: `"" in anything` is True, so a green that blanked the detail
        would satisfy a bare `not in` vacuously. Blanking it is one of the four
        mutations the coverage pass over `e44e069` measured as SURVIVING.
        """
        assert _CONTRADICTION_DETAIL != "", (
            "the developer detail must carry actual text -- a blank one makes every "
            "'the detail is not on the wire' assertion below vacuously true"
        )
        assert _CONTRADICTION_DETAIL not in refuse_a_flagged_value().message, (
            "the developer-facing detail names a domain class and a constructor "
            "signature; it rides the `from` chain for the log and must never become "
            "the sentence the client is handed"
        )
