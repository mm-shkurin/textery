from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from dto.generation.generation_request_dto import GenerationRequestDto
from dto.generation.generation_response_dto import (
    GenerationCreatedDto,
    GenerationDetailDto,
    GenerationSummaryDto,
)
from dto.shared.page_dto import PageDto
from generation.generate_document import GenerateDocument
from generation.get_generation import GetGeneration
from generation.list_generations import ListGenerations
from generation.request_generation import RequestGeneration
from security.current_owner import get_current_owner_id
from shared.page import DEFAULT_LIMIT

router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


def get_request_generation_usecase() -> RequestGeneration:
    raise NotImplementedError("wired by the application composition root")


def get_get_generation_usecase() -> GetGeneration:
    raise NotImplementedError("wired by the application composition root")


def get_generate_document_usecase() -> GenerateDocument:
    raise NotImplementedError("wired by the application composition root")


def get_list_generations_usecase() -> ListGenerations:
    raise NotImplementedError("wired by the application composition root")


@router.get("", response_model=PageDto[GenerationSummaryDto])
async def list_generations(
    limit: int = DEFAULT_LIMIT,
    cursor: Optional[str] = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ListGenerations = Depends(get_list_generations_usecase),
) -> PageDto[GenerationSummaryDto]:
    """The caller's own generation history, newest first.

    `limit`/`cursor` are plain parameters, not Query(ge=..., le=...): the bounds
    live in the domain's PageRequest so a violation answers this project's
    {error_code, message} rather than Pydantic's envelope -- the same reason
    IdempotencyKey is not a Header constraint.
    """
    page = await usecase.execute(owner_id=owner_id, limit=limit, cursor=cursor)
    return PageDto[GenerationSummaryDto](
        items=[GenerationSummaryDto.from_domain(generation) for generation in page.items],
        next_cursor=page.next_cursor,
    )


@router.post("", status_code=201, response_model=GenerationCreatedDto)
async def create_generation(
    request: GenerationRequestDto,
    background_tasks: BackgroundTasks,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: RequestGeneration = Depends(get_request_generation_usecase),
    generate_document: GenerateDocument = Depends(get_generate_document_usecase),
) -> GenerationCreatedDto:
    generation = await usecase.execute(
        owner_id=owner_id,
        topic=request.topic,
        volume_pages=request.volume_pages,
        requirements=request.requirements,
        extra_wishes=request.extra_wishes,
        document_type=request.document_type,
    )
    background_tasks.add_task(generate_document.execute, generation.id, generation.owner_id)
    return GenerationCreatedDto.from_domain(generation)


@router.get("/{generation_id}", response_model=GenerationDetailDto)
async def get_generation(
    generation_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: GetGeneration = Depends(get_get_generation_usecase),
) -> GenerationDetailDto:
    generation = await usecase.execute(generation_id, owner_id)
    if generation is None:
        # Absent and foreign are the same answer. The usecase's storage filters on
        # owner_id in SQL, so this branch cannot tell them apart.
        raise HTTPException(status_code=404, detail="generation not found")
    return GenerationDetailDto.from_domain(generation)
