from dataclasses import dataclass


@dataclass(frozen=True)
class TitleUpdate:
    """Three-state title intent carried across the save port.

    `title: str | None` can no longer express intent once a blank title means
    "preserve" -- `None` would be ambiguous between preserve and clear. This
    value object names the intent instead, so the rest adapter's Pydantic
    details never reach the usecase.
    """

    # No default: `TitleUpdate()` would be a second, unnamed way to build the
    # preserve state, which is the ambiguity the named factories below exist to
    # remove. `preserve()` and `of()` are the only doors.
    value: str | None

    @classmethod
    def preserve(cls) -> "TitleUpdate":
        return cls(value=None)

    @classmethod
    def of(cls, value: str) -> "TitleUpdate":
        return cls(value=value)

    def carries_a_value(self) -> bool:
        """Does this intent name a title to write, rather than preserve the stored one?

        The three-state intent is what this VO exists to express, so reading it
        must not mean null-testing `value` at the call site -- that is exactly the
        `str | None` ambiguity the class replaces, re-derived one layer out.
        `preserve()` is the only false case.
        """
        return self.value is not None

    def is_blank(self) -> bool:
        """Does this carry a value that is empty once whitespace is discounted?

        Blankness is TESTED, never applied -- `value` is left byte-for-byte, so a
        legitimate `" Отчёт "` keeps its padding. The rejected `value.strip() or
        None` would have trimmed every real title as a side effect; see
        decisions/blank-title-semantics-decision.md.
        """
        return self.value is not None and self.value.strip() == ""
