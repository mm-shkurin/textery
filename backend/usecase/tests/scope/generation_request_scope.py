from dataclasses import dataclass
from typing import ClassVar, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class GenerationRequestScope:
    document_type: str
    topic: Optional[str]
    volume_pages: Optional[int]
    requirements: Optional[str]
    extra_wishes: Optional[str]
    owner_id: UUID

    DEFAULTS: ClassVar[dict] = {
        "document_type": "доклад",
        "topic": "Как работает фотосинтез",
        "volume_pages": 3,
        "requirements": None,
        "extra_wishes": None,
    }

    @classmethod
    def builder(cls, **overrides) -> "GenerationRequestScope":
        # owner_id defaults to a fresh uuid per scope rather than a shared constant:
        # a module-level default would make every scope in a test share one owner, so
        # a cross-owner test that forgot to override it would pass vacuously.
        return cls(**{"owner_id": uuid4(), **cls.DEFAULTS, **overrides})
