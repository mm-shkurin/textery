"""The device language, read off an `Accept-Language` header.

The stored value is the canonical lower-case BCP-47 tag of the **highest-q**
entry (`14_AnalyticsEventTracking.md`, "device language"). Unparseable or absent
stores NULL, never a default: `en` written where nothing was sent is a
fabricated fact that Story 15 cannot tell from a real English visitor.

Canonicalized under an invariant lower-case (`01_API_Tests.md` §7.13) --
`str.lower()` in Python is already locale-independent, which is the property
that matters here: under a Turkish locale a locale-sensitive fold turns `TR-tr`
into `tr-tr` with a dotless i and the same header would store two different tags
depending on which host answered.
"""

from shared import limits

MAX_HEADER_LENGTH = limits.MAX_LANGUAGE_HEADER_LENGTH
MAX_ENTRIES = 32

_DEFAULT_QUALITY = 1.0


def language_tag_of(accept_language: str | None) -> str | None:
    """The highest-priority tag, or `None` when the header says nothing usable."""
    if not accept_language or len(accept_language) > MAX_HEADER_LENGTH:
        return None
    ranked = _ranked_entries(accept_language)
    if not ranked:
        return None
    # `max` over the quality alone, so ties keep the order the header listed --
    # `max` is documented to return the first maximal element, and the header's
    # own order is the only tie-break a client actually expressed.
    return max(ranked, key=lambda entry: entry[1])[0]


def _ranked_entries(accept_language: str) -> list[tuple[str, float]]:
    entries = accept_language.split(",")[:MAX_ENTRIES]
    ranked = [_parsed(entry) for entry in entries]
    # A `q=0` entry is not a preference, it is an explicit refusal of that
    # language, and storing it as the device language would invert the header's
    # meaning on `en;q=0, fr` -- which asks for French and rules out English.
    return [entry for entry in ranked if entry is not None and entry[1] > 0]


def _parsed(entry: str) -> tuple[str, float] | None:
    parts = entry.split(";")
    tag = _canonical(parts[0])
    if tag is None:
        return None
    return tag, _quality(parts[1:])


def _canonical(raw_tag: str) -> str | None:
    """One tag, lower-cased, or `None` when it is not a language tag at all.

    `*` is dropped rather than stored: it is a wildcard meaning "anything", and
    an account whose device language is `*` claims a language nobody speaks.
    """
    tag = raw_tag.strip().lower()
    if not tag or tag == "*":
        return None
    if not all(part.isalnum() for part in tag.split("-") if part != ""):
        return None
    return tag


def _quality(parameters: list[str]) -> float:
    """The entry's `q` value, defaulting to 1.0 as RFC 9110 specifies.

    A `q` that is present but unreadable falls back to the default rather than
    dropping the entry: the tag itself is still a usable statement of preference,
    and discarding it would let one malformed parameter promote a lower-priority
    language to the stored value.
    """
    for parameter in parameters:
        name, _, value = parameter.partition("=")
        if name.strip().lower() != "q":
            continue
        try:
            return float(value.strip())
        except ValueError:
            return _DEFAULT_QUALITY
    return _DEFAULT_QUALITY
