from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GenerationResponseDto:
    status_code: int
    body: Optional[dict]
