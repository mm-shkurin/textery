"""The documents resource, minus the list route.

`GET ""` lives in `document_list_router` and `DELETE /{id}` in
`document_deletion_router`; all three carry this prefix, so the reader of a URL
cannot tell they were split. Query parameters here arrive as raw `str | None` for
the reason that module states: a typed annotation answers a malformed value in
Pydantic's envelope instead of this API's `{error_code, message}`.
"""

from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from document.create_document import CreateDocument
from document.create_document_from_generation import CreateDocumentFromGeneration
from document.export_document import ExportDocument
from document.get_document import GetDocument
from document.save_document import SaveDocument
from dto.document.create_document_from_generation_request_dto import (
    CreateDocumentFromGenerationRequestDto,
)
from dto.document.create_document_request_dto import CreateDocumentRequestDto
from dto.document.document_response_dto import DocumentResponseDto
from dto.document.export_media_type import media_type_for
from dto.document.get_document_response_dto import GetDocumentResponseDto
from dto.document.save_document_request_dto import SaveDocumentRequestDto
from router import api_routes
from security.current_owner import get_current_owner_id
from shared.exceptions import NotFoundException

router = APIRouter(prefix=api_routes.DOCUMENTS, tags=["documents"])


def get_create_document_usecase() -> CreateDocument:
    raise NotImplementedError("wired by the application composition root")


def get_get_document_usecase() -> GetDocument:
    raise NotImplementedError("wired by the application composition root")


def get_save_document_usecase() -> SaveDocument:
    raise NotImplementedError("wired by the application composition root")


def get_export_document_usecase() -> ExportDocument:
    raise NotImplementedError("wired by the application composition root")


def get_create_document_from_generation_usecase() -> CreateDocumentFromGeneration:
    raise NotImplementedError("wired by the application composition root")


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
    # Stream the rendered bytes back verbatim as a binary attachment. The
    # Content-Type is derived HERE from the format the usecase rendered under:
    # naming `application/pdf` is a wire decision, and the usecase that used to
    # hold that map was speaking the transport it is meant to be free of.
    #
    # The filename is RFC 5987 percent-encoded. safe="" encodes control chars too
    # (CR->%0D, LF->%0A), so a title carrying raw CRLF cannot inject a header line;
    # unreserved chars and the dot stay literal, space -> %20, Cyrillic -> %XX.
    encoded = quote(rendered.filename, safe="")
    return Response(
        content=rendered.content,
        media_type=media_type_for(rendered.export_format),
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


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
        title=request.title,
    )
    return DocumentResponseDto.from_domain(document)
