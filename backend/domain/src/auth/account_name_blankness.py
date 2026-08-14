"""Does this value render as nothing?

Split from `account_name` so the predicate and its evidence stay readable, and
because the list below is the part that will grow: it is a denylist of characters
that occupy no pixels, and Unicode keeps making more of them.

The starting point was `required_topic()` in
`backend/domain/src/generation/generation_validation.py` -- whitespace and
category `Cf`. Reused verbatim it is not enough for a name, because a name is
RENDERED as an identity: it becomes the header's avatar initial and the
`aria-label` of the profile menu. A value that survives this check but draws
nothing gives the account a blank identity AND suppresses the email fallback that
would otherwise have made the row readable -- strictly worse than having no name
at all, which the fallback handles correctly.

The acceptance criteria list only U+200B, U+FEFF and U+00A0. All three are already
whitespace-or-`Cf`, so a test written from that list alone goes green against the
borrowed predicate and proves nothing. The characters below are the ones that do
not.
"""

import unicodedata

# Invisible, and NOT whitespace, and NOT category Cf -- so nothing generic catches
# them. Each is a real code point a real input method can produce.
# Listed as code points and built with chr(), never written as the characters
# themselves: they are invisible, so a literal in this file is a blank spot that
# an editor, a merge, or a copy-paste can drop without leaving anything visible in
# the diff. As numbers they are greppable and reviewable.
INVISIBLE_NON_FORMAT_CODE_POINTS = (
    0x115F,  # HANGUL CHOSEONG FILLER, category Lo
    0x1160,  # HANGUL JUNGSEONG FILLER, category Lo
    0x3164,  # HANGUL FILLER, category Lo
    0xFFA0,  # HALFWIDTH HANGUL FILLER, category Lo
    0x2800,  # BRAILLE PATTERN BLANK, category So
    0x17B4,  # KHMER VOWEL INHERENT AQ, category Mn
    0x17B5,  # KHMER VOWEL INHERENT AA, category Mn
)

INVISIBLE_NON_FORMAT_CHARACTERS = frozenset(
    chr(code_point) for code_point in INVISIBLE_NON_FORMAT_CODE_POINTS
)


def is_blank_after_stripping_invisibles(value: str) -> bool:
    """True when nothing in `value` would draw.

    Three strippers, because no one of them covers the others: `str.isspace()`
    handles the `Z*` separators, category `Cf` handles the zero-width and
    bidi-control formatters (U+200B, U+FEFF), and the explicit set above handles
    the fillers that are ordinary letters and symbols as far as Unicode is
    concerned.

    `Cc`/`Cs` are absent from all three deliberately: they never reach here.
    `AccountName` rejects them outright before normalization, so treating them as
    "blank" would be a second, contradictory policy for the same input.
    """
    return not any(_draws_something(char) for char in value)


def _draws_something(char: str) -> bool:
    if char.isspace() or char in INVISIBLE_NON_FORMAT_CHARACTERS:
        return False
    return unicodedata.category(char) != "Cf"
