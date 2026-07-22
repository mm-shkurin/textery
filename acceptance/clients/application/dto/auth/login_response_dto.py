from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LoginResponseDto:
    status_code: int
    body: Optional[dict]
