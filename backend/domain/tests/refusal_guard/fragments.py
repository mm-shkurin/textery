"""The fragment set the refusal guard leans on, and the proof it discriminates.

Extracted from `test_title_update_refusal_safety.py` when that file hit the
200-line cap. The split is by CONCERN, not by line count: this module owns WHICH
fragments are forbidden and WHY each one is a meaningful signal, while the two
test files that import it own the two separate claims made with them --
`test_title_update_refusal_safety.py` that no echoed field contains one, and
`test_title_update_refusal_fragments.py` that the list itself is not degenerate.
Every guard that lived in the original file is still live; nothing was dropped to
buy the room.

Not a `Statements` class, deliberately: there are ZERO Statements packages under
`backend/` (they exist only in `acceptance/statements/`), and domain tests assert
inline against module-level constants. This is that convention, hoisted one
directory up so two test modules can share one list -- a list that drifted
between them would guard one JSON key more strictly than the other for no stated
reason, which is the exact hazard the original file's single list existed to
prevent.
"""

import re

import pytest

from document.title_update import TitleUpdate
from shared.exceptions import ValidationException

# The value that, paired with a clear, IS the refusal -- spelled once. A plain
# `str` is safe to bind at module scope, the same as the siblings' `PADDED_TITLE`.
# What must NOT reach module or class-body scope is the CONSTRUCTION below that
# uses it: constructing it raises, and a raise during COLLECTION errors the whole
# module instead of failing one test -- the 65ec3fd defect the sibling files state
# at their heads. Hence the helper, whose body runs inside each test.
FLAGGED_VALUE = "Привет"


def _as_identifier_spelling(name: str) -> str:
    """`TitleUpdate` -> `TITLE_UPDATE`: the same name as an error code would spell it."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


# The four fragments, named once because the SAME family must be excluded from
# every field the handler echoes verbatim.
#
# `TitleUpdate.__name__` rather than the string "TitleUpdate": the guard is about
# the class this refusal belongs to, so a rename carries it along instead of
# silently retiring it. Reading `__name__` at module scope is safe under the
# collection rule the sibling files state -- it is an attribute of an already
# imported class object, not a construction of the value object.
#
# THE FOURTH IS THE SEPARATED SPELLING, and adding it is a deliberate reversal of
# the carve-out the original file wrote down. That carve-out -- "collapsing
# separators would start matching the ordinary English words in any legitimate
# rewrite of a sentence about titles, turning this guard into a veto on its own
# subject" -- is still correct FOR ENGLISH PROSE and is why the fragment is the
# `SCREAMING_SNAKE` spelling and not a general separator-collapsing match. The
# asymmetry is the decision: an `error_code` is an IDENTIFIER, so it can never
# contain `(`, can never contain `=`, and can never contain `TitleUpdate`
# contiguously -- the three original fragments were structurally unable to fire on
# that surface, and the realistic leak `INVALID_TITLE_UPDATE_CLEARS_WITH_VALUE`
# passed all three. In an identifier there is no "ordinary English" reading of
# `TITLE_UPDATE` to veto: the underscore is the identifier's word separator, not a
# hyphenated turn of phrase, so the argument that protects prose has no purchase
# here. `title_update` likewise does not occur in any sentence a human would
# write, so carrying the fourth fragment on the message surface too costs nothing
# and keeps one list across both fields.
FORBIDDEN_FRAGMENTS = [
    pytest.param("(", id="call-or-constructor-syntax"),
    pytest.param("=", id="keyword-argument-syntax"),
    pytest.param(TitleUpdate.__name__, id="domain-class-name"),
    pytest.param(_as_identifier_spelling(TitleUpdate.__name__), id="domain-class-name-as-code"),
]

# The negative control's baselines: text known to be SAFE, against which a
# fragment that fires is proven degenerate rather than proven a leak.
#
# FROZEN TEST-LOCAL COPIES of today's shipped strings, and NOT the production
# constants, which is the whole point. Reading the live `INVALID_TITLE_INTENT_
# MESSAGE` / `INVALID_TITLE_INTENT_ERROR_CODE` here would INVERT the diagnosis at
# the moment it matters: inject the real leak `INVALID_TITLE_UPDATE_CLEARS_WITH_
# VALUE` into production and a live baseline would report "your fragment list is
# broken" about a fragment that had just done its job. A baseline must be a
# fixed point the guard is measured against, so it is spelled here and moves only
# when a human decides some other sentence is the known-safe one.
KNOWN_SAFE_MESSAGE = "A title cannot be set and cleared at the same time."
KNOWN_SAFE_ERROR_CODE = "INVALID_TITLE_INTENT"

KNOWN_SAFE_SURFACES = [
    pytest.param("message", KNOWN_SAFE_MESSAGE, id="baseline-message"),
    pytest.param("error_code", KNOWN_SAFE_ERROR_CODE, id="baseline-error-code"),
]


def assert_fragment_discriminates(surface: str, baseline: str, forbidden: str) -> None:
    """A fragment present in known-safe text cannot tell a leak from safe prose.

    Stated as a PRECONDITION on the guard as well as a test of its own, so the
    six leak arms report the fragment-list defect instead of six confident,
    wrong accusations against text that is fine. The concrete way this happens:
    rename `TitleUpdate` -> `Title` and the derived fragments become `Title` and
    `TITLE`, both of which are in the shipped message AND in the shipped code.
    Every arm goes red at once against text nobody touched, and the cheapest
    unblock under that pressure is to delete the only prose arm the guard has.
    """
    assert forbidden.casefold() not in baseline.casefold(), (
        f"FRAGMENT-LIST DEFECT, not a leak: {forbidden!r} occurs in the known-safe "
        f"{surface} {baseline!r}, so it cannot distinguish an internal shape from "
        f"ordinary safe text and every assertion made with it is noise. Fix the "
        f"fragment list -- do NOT 'fix' the refusal text it is accusing"
    )


def assert_carries_no_internal_shape(surface: str, text: str, forbidden: str) -> None:
    """Both halves of one claim, for whichever echoed field `surface` names.

    The non-blank guard first, and not as a formality: fragments that can never
    be empty still assert NOTHING against an empty string, because `"(" not in
    ""` is True -- so a green that blanked the field would pass every param
    vacuously. Nor does the sibling's `==` drift pin cover it: that pin compares
    against a test-LOCAL literal, so the very coordinated edit this file exists
    to catch blanks both sides at once and stays green. `.strip()` rather than
    `!= ""`, because all-whitespace is equally vacuous here and equally useless
    to the client reading it.

    CASE-INSENSITIVE, decided rather than inherited: a message naming our type as
    "titleupdate" or "TITLEUPDATE" leaks exactly as much as the exact spelling,
    and `casefold()` costs nothing on `(` and `=`, which have no case.
    """
    assert text.strip() != "", (
        f"the refusal's {surface} must carry actual text -- a blank one makes every "
        f"'this fragment is not on the wire' assertion vacuously true, and hands the "
        f"client a 4xx that says nothing"
    )
    assert_fragment_discriminates(surface, _baseline_for(surface), forbidden)
    assert forbidden.casefold() not in text.casefold(), (
        f"the client-facing {surface} must not contain {forbidden!r} -- "
        f"`validation_exception_handler` echoes it verbatim into the response body, "
        f"so source syntax or a domain class name in it is a leak (Security 5.1), "
        f"not merely untidy prose"
    )


def _baseline_for(surface: str) -> str:
    return {"message": KNOWN_SAFE_MESSAGE, "error_code": KNOWN_SAFE_ERROR_CODE}[surface]


def refuse_a_flagged_value() -> ValidationException:
    """The one call under test, so no test below re-spells the raise.

    A helper rather than a fixture: it must run INSIDE the assertion's test so
    that a green which stops raising fails these tests rather than erroring them.
    """
    with pytest.raises(ValidationException) as refusal:
        TitleUpdate(value=FLAGGED_VALUE, clears=True)
    return refusal.value
