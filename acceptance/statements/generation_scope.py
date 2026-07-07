from dataclasses import dataclass
from typing import ClassVar, Optional


@dataclass(frozen=True)
class GenerationScope:
    document_type: str
    topic: Optional[str]
    volume_pages: Optional[int]
    requirements: Optional[str]
    extra_wishes: Optional[str]

    DEFAULTS: ClassVar[dict] = {
        "document_type": "доклад",
        "topic": "Как работает фотосинтез",
        "volume_pages": 3,
        "requirements": None,
        "extra_wishes": None,
    }

    @classmethod
    def builder(cls, **overrides) -> "GenerationScope":
        return cls(**{**cls.DEFAULTS, **overrides})
