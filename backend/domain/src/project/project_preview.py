import re
import unicodedata

from shared import limits

# Unicode code points, matching `preview` in api-specs/projects_list.yaml.
PREVIEW_MAX_CODE_POINTS = limits.PREVIEW_MAX_CODE_POINTS
# How much stored content the projection needs in hand to produce that preview.
# Markup and collapsed whitespace shrink the text, so the bounded prefix the
# storage adapter reads must be larger than the output -- but it must still be
# *bounded*, or the bytes a page reads grow with stored document size.
PREVIEW_SOURCE_MAX_CHARS = limits.PREVIEW_SOURCE_MAX_CHARS
_TAG = re.compile(r"<[^>]*>")
_WHITESPACE = re.compile(r"\s+")

# Trailing code points that are not a character of their own: a combining mark
# belongs to the base character before it, and a zero-width joiner promises a
# character after it. Cutting on either leaves a lone accent or a dangling
# joiner where the user stored one glyph.
_ZERO_WIDTH_JOINER = "‍"
_COMBINING_CATEGORIES = frozenset({"Mn", "Mc", "Me"})


def _is_continuation(character: str) -> bool:
    return (
        character == _ZERO_WIDTH_JOINER or unicodedata.category(character) in _COMBINING_CATEGORIES
    )


def derive_preview(content: str | None) -> str:
    """A bounded plain-text preview of stored document content.

    Markup is stripped **before** truncation, never after: cutting HTML at a
    length bound and stripping the remainder is how a preview emits an unbalanced
    tag, and cutting after stripping cannot. The stored content is sanitized HTML
    (story 18), so this is a second, narrower guarantee -- the feed returns text,
    and a renderer that forgets to escape one field is not handed markup to
    re-inject.

    The result is trimmed back to a whole character rather than split: a ZWJ
    emoji sequence or a combining accent astride the limit would otherwise emit a
    lone mark or a dangling joiner.
    """
    if not content:
        return ""
    text = _TAG.sub(" ", content[:PREVIEW_SOURCE_MAX_CHARS])
    text = unicodedata.normalize("NFC", text)
    text = _WHITESPACE.sub(" ", text).strip()
    if len(text) <= PREVIEW_MAX_CODE_POINTS:
        return text
    cut = PREVIEW_MAX_CODE_POINTS
    # Walk back off any continuation code points, and off the joiner that would
    # then be left trailing. Bounded by `cut > 0`, so a string made entirely of
    # combining marks yields "" rather than looping.
    while cut > 0 and _is_continuation(text[cut]):
        cut -= 1
    while cut > 0 and text[cut - 1] == _ZERO_WIDTH_JOINER:
        cut -= 1
    return text[:cut].rstrip()
