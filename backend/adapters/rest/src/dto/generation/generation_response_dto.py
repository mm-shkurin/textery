from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from generation.generation import Generation


class GenerationCreatedDto(BaseModel):
    generation_id: str
    status: str
    created_at: datetime
    topic: Optional[str]
    volume_pages: Optional[int]
    document_type: str

    @classmethod
    def from_domain(cls, generation: Generation) -> "GenerationCreatedDto":
        return cls(
            generation_id=str(generation.id),
            status=generation.status,
            created_at=generation.created_at,
            topic=generation.topic,
            volume_pages=generation.volume_pages,
            document_type=generation.document_type,
        )


# The create and list responses are the same projection: generations_create.yaml and
# generations_list.yaml both name the schema GenerationResponse, with the same fields.
# One class rather than an identical twin, so the two cannot drift apart; the alias
# just makes the list router read honestly.
GenerationSummaryDto = GenerationCreatedDto


class GenerationDetailDto(BaseModel):
    generation_id: str
    status: str
    created_at: datetime
    topic: Optional[str]
    volume_pages: Optional[int]
    document_type: str
    content: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_domain(cls, generation: Generation) -> "GenerationDetailDto":
        return cls(
            generation_id=str(generation.id),
            status=generation.status,
            created_at=generation.created_at,
            topic=generation.topic,
            volume_pages=generation.volume_pages,
            document_type=generation.document_type,
            content=generation.content,
            error_message=generation.error_message,
        )
