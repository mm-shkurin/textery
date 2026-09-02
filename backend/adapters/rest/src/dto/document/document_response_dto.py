from document.document import Document
from dto.document.document_identity_dto import DocumentIdentityDto


class DocumentResponseDto(DocumentIdentityDto):
    content: str
    # Additive on the shape story 5 shipped (documents_from_generation.yaml says
    # so explicitly): null for a manual document, set for a converted one. Existing
    # consumers tolerate them because both are optional on the wire.
    title: str | None = None
    generation_id: str | None = None

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentResponseDto":
        # Built from the entity the usecase returns, never from the request DTO.
        # That is what makes scenario 7.2 structural: the response cannot show
        # unsanitized content, because it never has access to it.
        return cls(
            **cls.identity_of(document),
            content=document.content,
            title=document.title,
            generation_id=str(document.generation_id) if document.generation_id else None,
        )
