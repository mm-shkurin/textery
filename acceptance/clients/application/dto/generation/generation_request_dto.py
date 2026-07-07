from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class CreateGenerationRequestDto:
    document_type: str
    topic: Optional[str] = None
    volume_pages: Optional[int] = None
    requirements: Optional[str] = None
    extra_wishes: Optional[str] = None

    def to_json(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}
