from pydantic import BaseModel


class GenerationRequestDto(BaseModel):
    document_type: str
    topic: str | None = None
    volume_pages: int | None = None
    requirements: str | None = None
    extra_wishes: str | None = None
