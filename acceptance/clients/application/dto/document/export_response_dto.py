from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExportResponseDto:
    status_code: int
    body: Optional[dict]
    content_type: Optional[str]
    content_disposition: Optional[str]
    content: bytes
