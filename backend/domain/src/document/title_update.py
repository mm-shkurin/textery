from dataclasses import dataclass


@dataclass(frozen=True)
class TitleUpdate:
    """Three-state title intent carried across the save port.

    `title: str | None` can no longer express intent once a blank title means
    "preserve" -- `None` would be ambiguous between preserve and clear. This
    value object names the intent instead, so the rest adapter's Pydantic
    details never reach the usecase.
    """

    value: str | None = None

    @classmethod
    def preserve(cls) -> "TitleUpdate":
        return cls(value=None)

    @classmethod
    def of(cls, value: str) -> "TitleUpdate":
        return cls(value=value)

    def is_blank(self) -> bool:
        """Does this carry a value that is empty once whitespace is discounted?

        Blankness is TESTED, never applied -- `value` is left byte-for-byte, so a
        legitimate `" Отчёт "` keeps its padding. The rejected `value.strip() or
        None` would have trimmed every real title as a side effect; see
        decisions/blank-title-semantics-decision.md.
        """
        return self.value is not None and self.value.strip() == ""
