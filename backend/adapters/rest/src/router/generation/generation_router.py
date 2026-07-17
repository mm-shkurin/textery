from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from dto.generation.generation_request_dto import GenerationRequestDto
from dto.generation.generation_response_dto import GenerationCreatedDto, GenerationDetailDto
from generation.generate_document import GenerateDocument
from generation.get_generation import GetGeneration
from generation.request_generation import RequestGeneration
from security.current_owner import get_current_owner_id

router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


def get_request_generation_usecase() -> RequestGeneration:
    raise NotImplementedError("wired by the application composition root")


def get_get_generation_usecase() -> GetGeneration:
    raise NotImplementedError("wired by the application composition root")


def get_generate_document_usecase() -> GenerateDocument:
    raise NotImplementedError("wired by the application composition root")


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
