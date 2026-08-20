from pydantic import BaseModel

from document.document import Document
from document.page_settings import PageSettings
from dto.document.document_identity_dto import DocumentIdentityDto


class PageSettingsDto(BaseModel):
    """The nine read-side keys `documents_get.yaml` declares under PageSettings.

    Every key is required on this shape: it is only ever built from a stored
    PageSettings, and a defaulted field here would let a partially-written row
    read back as today's preset — the exact confusion this story exists to
    prevent. Absence is carried one level up, as `page_settings: null`.
    """

    page_size: str
    orientation: str
    margins_mm: dict[str, float]
    font_size_pt: float
    line_height: float
    header_text: str | None
    footer_text: str | None
    show_page_numbers: bool
    skip_number_on_first_page: bool

    @classmethod
    def from_domain(cls, page_settings: PageSettings) -> "PageSettingsDto":
        return cls(
            page_size=page_settings.page_size,
            orientation=page_settings.orientation,
            margins_mm=dict(page_settings.margins_mm),
            font_size_pt=page_settings.font_size_pt,
            line_height=page_settings.line_height,
            header_text=page_settings.header_text,
            footer_text=page_settings.footer_text,
            show_page_numbers=page_settings.show_page_numbers,
            skip_number_on_first_page=page_settings.skip_number_on_first_page,
        )


class GetDocumentResponseDto(DocumentIdentityDto):
    """The read shape, and only the read shape: GET /documents/{document_id}.

    Separate from DocumentResponseDto rather than an extension of it because the
    two contracts genuinely differ. documents_get.yaml declares exactly the eight
    keys below — no `title`, no `generation_id` — while the three write-shaped
    routes (POST /documents, POST /documents/from-generation, PUT
    /documents/{id}) mandate both, and documentFromGenerationApi.ts reads them
    non-nullably. Widening the shared DTO with page_settings would have leaked
    the write-only keys onto the read; narrowing it would have broken the writes.

    `page_settings` is `| None = None` so the key is always PRESENT on the wire:
    SQL NULL -> domain None -> JSON null. An omitted key would say "this server
    does not know the field", which is a different answer than "never
    configured". No default preset is constructed anywhere on this path.
    """

    content: str
    page_settings: PageSettingsDto | None = None

    @classmethod
    def from_domain(cls, document: Document) -> "GetDocumentResponseDto":
        return cls(
            **cls.identity_of(document),
            content=document.content,
            page_settings=(
                PageSettingsDto.from_domain(document.page_settings)
                if document.page_settings is not None
                else None
            ),
        )
