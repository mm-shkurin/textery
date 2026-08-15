import unicodedata
from dataclasses import dataclass

from shared.exceptions import ValidationException

# Unicode code points, not bytes and not UTF-16 units. A byte bound would refuse
# a legal 200-character Cyrillic query, and OpenAPI's `maxLength` counts UTF-16
# units, which disagrees with this on astral-plane input at exactly the boundary
# the tests assert.
QUERY_MAX_CODE_POINTS = 200

# The character that makes `%` and `_` literal in a SQL LIKE pattern. Escaping it
# first is not optional: a query containing a lone backslash would otherwise
# escape whatever the caller typed next.
LIKE_ESCAPE = "\\"
_LIKE_METACHARACTERS = (LIKE_ESCAPE, "%", "_")


@dataclass(frozen=True)
class ProjectQuery:
    """A validated, normalized search term -- or the absence of one.

    Absence is a value here rather than `None` at every call site: the storage
    adapter asks `is_present` instead of each caller remembering that
    whitespace-only means "no search" rather than "match nothing".
    """

    text: str | None

    @classmethod
    def absent(cls) -> "ProjectQuery":
        return cls(text=None)

    @classmethod
    def parse(cls, raw: str | None) -> "ProjectQuery":
        """The term to search for, NFC-normalized and trimmed.

        Normalization happens on this side as well as on the stored side, so a
        title saved in NFD is found by its NFC form and vice versa -- two strings
        that a user cannot tell apart must not match differently.

        The length bound is measured *after* normalization, because that is the
        string the database will see.
        """
        if raw is None:
            return cls.absent()
        normalized = unicodedata.normalize("NFC", raw).strip()
        if normalized == "":
            # Whitespace-only is "no search", not "match nothing": a user who
            # taps space in the box expects their feed, not an empty screen.
            return cls.absent()
        if len(normalized) > QUERY_MAX_CODE_POINTS:
            raise ValidationException(
                message=f"q must be at most {QUERY_MAX_CODE_POINTS} characters.",
                error_code="INVALID_QUERY",
            )
        return cls(text=normalized)

    @property
    def is_present(self) -> bool:
        return self.text is not None

    def like_pattern(self) -> str:
        """The term as a substring LIKE pattern with its metacharacters escaped.

        Parameter binding stops injection; it does *not* stop `%` from meaning
        "anything". Unescaped, a query of `%` degenerates into a full scan that
        matches every row -- the single most expensive request this endpoint can
        be asked to serve, produced by one keystroke.
        """
        if self.text is None:
            raise ValueError("an absent query has no pattern")
        escaped = self.text
        for metacharacter in _LIKE_METACHARACTERS:
            escaped = escaped.replace(metacharacter, LIKE_ESCAPE + metacharacter)
        return f"%{escaped}%"
