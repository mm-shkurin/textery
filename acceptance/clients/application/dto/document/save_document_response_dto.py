from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SaveDocumentResponseDto:
    status_code: int
    body: Optional[dict]
