from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateGenerationRequestDto:
    document_type: str
    topic: Optional[str] = None
    volume_pages: Optional[int] = None
    requirements: Optional[str] = None
    extra_wishes: Optional[str] = None

    def to_json(self) -> dict:
        payload: dict = {"document_type": self.document_type}
        if self.topic is not None:
            payload["topic"] = self.topic
        if self.volume_pages is not None:
            payload["volume_pages"] = self.volume_pages
        if self.requirements is not None:
            payload["requirements"] = self.requirements
        if self.extra_wishes is not None:
            payload["extra_wishes"] = self.extra_wishes
        return payload
