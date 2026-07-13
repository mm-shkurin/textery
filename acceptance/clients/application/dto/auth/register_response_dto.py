from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegisterResponseDto:
    status_code: int
    body: Optional[dict]
