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
