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
ORTHOGONAL by construction: the `==` pin rules out every message except one and
DIES on any rewrite -- which is precisely why it cannot stand alone, and why this
file exists; this one rules out a FAMILY of messages and SURVIVES every rewrite,
which is what makes it useless as a drift detector. Neither subsumes the other,
and only the pair is closed under a coordinated edit.

Both surfaces are read off a LIVE RAISED EXCEPTION, never off the constants.
Asserting the property on `INVALID_TITLE_INTENT_MESSAGE` alone would leave the
raise free to pass a different string entirely, and would pin the safety of a
constant rather than the safety of what a client actually receives.

BOTH verbatim-echoed fields are covered, not one. `validation_exception_handler`
returns `{"error_code": exc.error_code, "message": exc.message}` with neither
substituted, so guarding only the message leaves the identical coordinated-edit
hole open one JSON key over -- `error_code`'s content is otherwise pinned only by
a tuple `==` against a test-LOCAL literal in the sibling file.

The production constant IS imported here, unlike the literal in the sibling
file, and for the same reason that made the literal right there: an imported
constant makes an EQUALITY assertion tautological, but a PROPERTY assertion over
it is not -- the claim is about whatever the symbol holds, and the whole point is
that it must hold under any future edit. Re-typing the sentence here would put
the guard back on bytes.

THE FRAGMENT LIST AND THE ASSERTION HELPER MOVED to `refusal_guard/fragments.py`
when this file reached the 200-line cap; that module states which fragments are
forbidden and why, including why the separated `TITLE_UPDATE` spelling is right
for an identifier surface and wrong for English prose. Its companion
`test_title_update_refusal_fragments.py` proves the list discriminates. Nothing
was dropped in the split.

ALREADY-GREEN REGRESSION GUARD. The current message,
"A title cannot be set and cleared at the same time.", satisfies both properties
today, so this file is expected to PASS on unmutated production -- the precedent
for landing such a guard live and unskipped is `red-adapter db (TitleUpdate
unwrap)` and `red-usecase (the raw-str arm of _title_intent)`. It is verified
against a kill-mutant rather than only against a green run, so that it is not
mistaken for a test that would pass over an empty message too.
"""

import pytest

from document.title_update import _CONTRADICTION_DETAIL
from refusal_guard.fragments import (
    FORBIDDEN_FRAGMENTS,
    assert_carries_no_internal_shape,
    refuse_a_flagged_value,
)


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

    @pytest.mark.parametrize("forbidden", FORBIDDEN_FRAGMENTS)
    def test_should_not_show_a_client_any_internal_shape_in_the_message(self, forbidden):
        """Four fragments, each the signature of a distinct leak.

        `(` and `=` together are what makes a sentence read as SOURCE -- every
        internal shape this message could grow (`TitleUpdate(value=..., clears=
        True)`, a repr, a field list) needs at least one of them, and neither has
        any business in a sentence written for a human. The class name is the
        third independently: a message could name `TitleUpdate` in prose, with no
        punctuation at all, and still tell a client what our domain types are
        called. The fourth is that same name spelled as an identifier would spell
        it, which no human sentence contains and every leaked code does.
        """
        assert_carries_no_internal_shape("message", refuse_a_flagged_value().message, forbidden)

    @pytest.mark.parametrize("forbidden", FORBIDDEN_FRAGMENTS)
    def test_should_not_show_a_client_any_internal_shape_in_the_error_code(self, forbidden):
        """The OTHER field the handler echoes unsubstituted, guarded identically.

        `exception_handlers.py` returns `error_code` and `message` side by side,
        both straight off the exception, and `test_should_return_400_with_error_
        code_and_message` pins that pass-through live. So an `error_code` is
        response body text on exactly the same terms as the message is, and the
        only thing standing between it and a leak was a tuple `==` in the sibling
        file against a test-LOCAL literal -- which the coordinated edit this file
        exists to catch defeats by rewriting both halves at once.

        This is not a theoretical surface for a code: the natural "make it more
        specific" edit is a discriminating suffix, and the discriminator to hand
        is the field pair that caused the refusal --
        `INVALID_TITLE_UPDATE_CLEARS_WITH_VALUE`. Three of the four fragments are
        structurally incapable of catching it, which is why the fourth exists.
        """
        assert_carries_no_internal_shape(
            "error_code", refuse_a_flagged_value().error_code, forbidden
        )

    def test_should_keep_the_developer_detail_off_the_client_message(self):
        """The specific text the properties above exist to keep out.

        `_CONTRADICTION_DETAIL` is the sentence the constructor USED to raise, and
        the one a future "more helpful message" edit would reach for first. Named
        here directly so the guard does not rest on the four fragments happening
        to cover it.

        Its non-emptiness is asserted in the same breath, and not as a
        formality: `"" in anything` is True, so a green that blanked the detail
        would satisfy a bare `not in` vacuously. Blanking it is one of the four
        mutations the coverage pass over `e44e069` measured as SURVIVING.

        `.strip()`, matching the haystack guard above and for the identical
        reason: `"   " in <anything>` is False, so an all-whitespace detail
        satisfies a bare `not in` just as vacuously as an empty one. The first
        version of this line used `!= ""` and let that mutant live.

        `.casefold()` on BOTH sides, which `202c0bc` decided for the fragment
        guard and then left off here in the same commit. Re-cased is the cheapest
        way to paste the detail back in while looking edited, and the reason the
        fragments are matched case-insensitively applies verbatim to a whole
        sentence: a client handed this text in any casing has been handed the
        constructor signature.
        """
        assert _CONTRADICTION_DETAIL.strip() != "", (
            "the developer detail must carry actual text -- a blank or all-whitespace "
            "one makes every 'the detail is not on the wire' assertion below vacuously true"
        )
        client_message = refuse_a_flagged_value().message
        assert _CONTRADICTION_DETAIL.casefold() not in client_message.casefold(), (
            "the developer-facing detail names a domain class and a constructor "
            "signature; it rides the `from` chain for the log and must never become "
            "the sentence the client is handed"
        )
