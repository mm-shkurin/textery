from pydantic import BaseModel


class CreateDocumentRequestDto(BaseModel):
    # Only document_type. status/id/content sent by a client are dropped by
    # Pydantic's default extra="ignore" -- see
    # 05-manual-mode/decisions/server-owned-fields-ignored-decision.md. The enum is
    # NOT declared here: the domain's DocumentType owns it, so a bad value surfaces
    # as 422 {error_code: INVALID_DOCUMENT_TYPE} rather than Pydantic's envelope.
    document_type: str
