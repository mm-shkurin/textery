from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID, uuid4


@dataclass(frozen=True)
class GenerationRequestScope:
    document_type: str
    topic: str | None
    volume_pages: int | None
    requirements: str | None
    extra_wishes: str | None
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
