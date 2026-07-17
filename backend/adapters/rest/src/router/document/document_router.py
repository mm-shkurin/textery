from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from document.create_document import CreateDocument
from document.get_document import GetDocument
from document.save_document import SaveDocument
from dto.document.document_dtos import (
    CreateDocumentRequestDto,
    DocumentResponseDto,
    SaveDocumentRequestDto,
)
from security.current_owner import get_current_owner_id
from shared.exceptions import NotFoundException

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_create_document_usecase() -> CreateDocument:
    raise NotImplementedError("wired by the application composition root")


def get_get_document_usecase() -> GetDocument:
    raise NotImplementedError("wired by the application composition root")


def get_save_document_usecase() -> SaveDocument:
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


@router.get("/{document_id}", response_model=DocumentResponseDto)
async def get_document(
    document_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: GetDocument = Depends(get_get_document_usecase),
) -> DocumentResponseDto:
    document = await usecase.execute(document_id=document_id, owner_id=owner_id)
    if document is None:
        # Absent and foreign are the same answer: the usecase's repository filters
        # on owner_id in SQL, so there is no branch here that could tell them apart
        # even by accident.
        raise NotFoundException(f"document {document_id} not found")
    return DocumentResponseDto.from_domain(document)


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
    )
    return DocumentResponseDto.from_domain(document)
