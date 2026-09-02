from uuid import UUID

from pydantic import BaseModel


class CreateDocumentFromGenerationRequestDto(BaseModel):
    """The conversion request body: one field, and it is an id the caller owns.

    Nothing else is accepted. `title`, `content`, `status`, `version` and even a
    spoofed `generation_id` on the response shape are server-derived, and
    Pydantic's default extra="ignore" drops them -- so a client cannot seed a
    document's text by POSTing it here. Same mass-assignment guard as
    CreateDocumentRequestDto, for the same reason.
    """

    generation_id: UUID
