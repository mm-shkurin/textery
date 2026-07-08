from typing import Optional

from pydantic import BaseModel


class GenerationRequestDto(BaseModel):
    document_type: str
    topic: Optional[str] = None
    volume_pages: Optional[int] = None
    requirements: Optional[str] = None
    extra_wishes: Optional[str] = None
