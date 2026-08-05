from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from document.create_document import CreateDocument
from document.create_document_from_generation import CreateDocumentFromGeneration
from document.export_document import ExportDocument
from document.get_document import GetDocument
from document.list_documents import ListDocuments
from document.save_document import SaveDocument
from document.title_update import TitleUpdate
from dto.document.document_dtos import (
    CreateDocumentFromGenerationRequestDto,
    CreateDocumentRequestDto,
    DocumentResponseDto,
    DocumentSummaryDto,
    SaveDocumentRequestDto,
)
from dto.document.get_document_response_dto import GetDocumentResponseDto
from dto.shared.page_dto import PageDto
from security.current_owner import get_current_owner_id
from shared.exceptions import NotFoundException
from shared.page import DEFAULT_LIMIT

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_create_document_usecase() -> CreateDocument:
    raise NotImplementedError("wired by the application composition root")


def get_get_document_usecase() -> GetDocument:
    raise NotImplementedError("wired by the application composition root")


def get_save_document_usecase() -> SaveDocument:
    raise NotImplementedError("wired by the application composition root")


def get_list_documents_usecase() -> ListDocuments:
    raise NotImplementedError("wired by the application composition root")


def get_export_document_usecase() -> ExportDocument:
    raise NotImplementedError("wired by the application composition root")


def get_create_document_from_generation_usecase() -> CreateDocumentFromGeneration:
    raise NotImplementedError("wired by the application composition root")


@router.get("", response_model=PageDto[DocumentSummaryDto])
async def list_documents(
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ListDocuments = Depends(get_list_documents_usecase),
) -> PageDto[DocumentSummaryDto]:
    """The caller's own document history, newest first.

    Declared before GET /{document_id} so the two cannot race: "" and "/{id}" are
    distinct paths to Starlette, but keeping the literal above the parameterised
    one is the habit that stops a future /documents/recent from being swallowed.
    """
    page = await usecase.execute(owner_id=owner_id, limit=limit, cursor=cursor)
    return PageDto[DocumentSummaryDto](
        items=[DocumentSummaryDto.from_domain(document) for document in page.items],
        next_cursor=page.next_cursor,
    )


@router.post("", response_model=DocumentResponseDto)
async def create_document(
    request: CreateDocumentRequestDto,
    response: Response,
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: CreateDocument = Depends(get_create_document_usecase),
) -> DocumentResponseDto:
    result = await usecase.execute(
        owner_id=owner_id,
        document_type=request.document_type,
        idempotency_key=idempotency_key,
    )
    # 201 for a fresh create, 200 for a replayed key. Set here rather than via the
    # decorator's status_code, which cannot vary per request.
    response.status_code = 200 if result.is_replay else 201
    return DocumentResponseDto.from_domain(result.document)


@router.post("/from-generation", response_model=DocumentResponseDto)
async def create_document_from_generation(
    request: CreateDocumentFromGenerationRequestDto,
    response: Response,
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: CreateDocumentFromGeneration = Depends(get_create_document_from_generation_usecase),
) -> DocumentResponseDto:
    """Convert a completed generation into the document the editor edits.

    Declared above GET/PUT /{document_id} for the same reason list_documents is
    declared above them: "from-generation" is a literal segment that a
    parameterised path could otherwise swallow. It does not today -- this is a
    POST and those are not -- but the ordering is the habit that keeps it true
    when a POST /{document_id}/... is added.
    """
    result = await usecase.execute(
        owner_id=owner_id,
        generation_id=request.generation_id,
        idempotency_key=idempotency_key,
    )
    # 201 for a fresh conversion, 200 when this generation was already converted
    # (a replay, or the loser of a concurrent race). Set here rather than on the
    # decorator, which cannot vary per request.
    response.status_code = 200 if result.is_replay else 201
    return DocumentResponseDto.from_domain(result.document)


@router.get("/{document_id}", response_model=GetDocumentResponseDto)
async def get_document(
    document_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: GetDocument = Depends(get_get_document_usecase),
) -> GetDocumentResponseDto:
    """The read shape only. GetDocumentResponseDto — not the shared
    DocumentResponseDto the three write routes return — because documents_get.yaml
    declares page_settings and declares neither title nor generation_id.
    """
    document = await usecase.execute(document_id=document_id, owner_id=owner_id)
    if document is None:
        # Absent and foreign are the same answer: the usecase's repository filters
        # on owner_id in SQL, so there is no branch here that could tell them apart
        # even by accident.
        raise NotFoundException(f"document {document_id} not found")
    return GetDocumentResponseDto.from_domain(document)


@router.get("/{document_id}/export")
async def export_document(
    document_id: UUID,
    format: str | None = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ExportDocument = Depends(get_export_document_usecase),
) -> Response:
    rendered = await usecase.execute(document_id=document_id, owner_id=owner_id, format=format)
    if rendered is None:
        # Absent and foreign collapse to the same None, translated into the
        # sanctioned 404 rather than leaking which case it was.
        raise NotFoundException(f"document {document_id} not found")
    # Stream the rendered bytes back verbatim as a binary attachment. media_type
    # is threaded from the RenderedExport so a future DOCX export is typed
    # correctly rather than mislabelled application/pdf.
    #
    # The filename is RFC 5987 percent-encoded. safe="" encodes control chars too
    # (CR->%0D, LF->%0A), so a title carrying raw CRLF cannot inject a header line;
    # unreserved chars and the dot stay literal, space -> %20, Cyrillic -> %XX.
    encoded = quote(rendered.filename, safe="")
    return Response(
        content=rendered.content,
        media_type=rendered.media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


def _title_update(request: SaveDocumentRequestDto) -> TitleUpdate:
    """The wire's four rows onto the three-state intent (story 17's ADR): absent
    and ""/"   " preserve, null clears, a real title sets VERBATIM.

    Decided HERE -- absent and an explicit null both arrive as `title=None` and
    only `model_fields_set` tells them apart. No blank branch (`__post_init__`
    folds a blank given to `of()`; one routed into `clear()` skips that fold and
    wipes a title) and no `.strip()` -- `" Отчёт "` keeps its padding.
    """
    if "title" not in request.model_fields_set:
        return TitleUpdate.preserve()
    if request.title is None:
        return TitleUpdate.clear()
    return TitleUpdate.of(request.title)


@router.put("/{document_id}", response_model=DocumentResponseDto)
async def save_document(
    document_id: UUID,
    request: SaveDocumentRequestDto,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: SaveDocument = Depends(get_save_document_usecase),
) -> DocumentResponseDto:
    document = await usecase.execute(
        document_id=document_id,
        owner_id=owner_id,
        content=request.content,
        version=request.version,
        title=_title_update(request),
    )
    return DocumentResponseDto.from_domain(document)
