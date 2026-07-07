from dataclasses import dataclass
from typing import ClassVar, Optional

from clients.application.dto.generation.generation_request_dto import CreateGenerationRequestDto


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

    def to_request_dto(self) -> CreateGenerationRequestDto:
        return CreateGenerationRequestDto(
            document_type=self.document_type,
            topic=self.topic,
            volume_pages=self.volume_pages,
            requirements=self.requirements,
            extra_wishes=self.extra_wishes,
        )
