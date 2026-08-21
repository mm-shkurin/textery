"""The five campaign parameters, and the fail-open rule that governs them.

`endpoints.md` § "Attribution is fail-open on both auth routes (`A1 + B2`)": on
`POST /auth/register` and `GET /auth/oauth/{provider}/start` the attribution set
decides only what is *stored*, never what is *answered*. Nothing here raises --
an unusable member returns the empty set, and the caller registers or is
redirected exactly as it would have been.

**The whole set, not the bad member (`B2`).** Dropping one member would write
attribution into the database that no marketing link ever produced --
`utm_source` present, `utm_campaign` silently missing -- and Story 15 cannot tell
that apart from a link that genuinely had no campaign. Discarding the set keeps
every stored attribution a faithful copy of one real link; the cost is paid in a
marketing report rather than by a user.
"""

import unicodedata
from dataclasses import dataclass

# Code points after NFC, not bytes. The bound guards how much of a marketing
# link is worth keeping, which is a text question; the byte caps in this story
# all sit at transport boundaries, where the unit is what was actually read.
MAX_VALUE_CODE_POINTS = 200

FIELD_NAMES = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


@dataclass(frozen=True)
class Attribution:
    """One marketing link's five parameters, or the empty set.

    Empty means "nothing to store" for every reason at once -- no `utm_*` at all,
    all of them blank, one of them over the bound, one of them undecodable. That
    collapse is deliberate: the five columns are NULL in every one of those cases,
    so a caller that could tell them apart would only be tempted to answer
    differently, which is exactly what the governing decision forbids.
    """

    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None

    @classmethod
    def of(cls, values: dict[str, str | None]) -> "Attribution":
        """The five stored values for a link, or the empty set. Never raises."""
        normalized: dict[str, str | None] = {}
        for field_name in FIELD_NAMES:
            member = _normalized(values.get(field_name))
            if isinstance(member, _Unusable):
                return cls()
            normalized[field_name] = member
        return cls(**normalized)  # type: ignore[arg-type]

    @property
    def is_empty(self) -> bool:
        return all(getattr(self, name) is None for name in FIELD_NAMES)

    def as_columns(self) -> dict[str, str | None]:
        return {name: getattr(self, name) for name in FIELD_NAMES}


# A sentinel rather than an exception: "this member is unusable" has to travel
# out of the per-field step without becoming a refusal anywhere up the stack,
# and `None` already means the legitimate "this member was not sent".
class _Unusable:
    """The sentinel's own type, so a caller that checks for it is left with the
    two storable answers -- `str` and `None` -- rather than with `object`."""


_UNUSABLE = _Unusable()


def _normalized(raw: object) -> "str | None | _Unusable":
    """One member's stored value, `None` when absent, `_UNUSABLE` when it is not.

    An explicitly empty parameter and an omitted one are the same stored state
    (`01_API_Tests.md` §7.9): a link ending `?utm_term=` carries no term.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        return _UNUSABLE
    value = unicodedata.normalize("NFC", raw).strip()
    if not value:
        return None
    if len(value) > MAX_VALUE_CODE_POINTS:
        return _UNUSABLE
    if not _is_storable(value):
        return _UNUSABLE
    return value


def _is_storable(value: str) -> bool:
    """Whether Postgres can hold this text at all.

    NUL is refused by every `text` column, and a lone surrogate -- what a cp1251
    link decoded as UTF-8 leaves behind -- cannot be encoded on the way to the
    driver. Both would surface as a driver error mid-registration, which is the
    one thing the fail-open rule exists to prevent.
    """
    if "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True
