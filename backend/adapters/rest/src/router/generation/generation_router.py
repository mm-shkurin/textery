from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from container import create_generate_document, create_get_generation, create_request_generation
from dto.generation.generation_request_dto import GenerationRequestDto
from dto.generation.generation_response_dto import GenerationCreatedDto, GenerationDetailDto
from generation.get_generation import GetGeneration
from generation.request_generation import RequestGeneration

router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


def get_request_generation_usecase() -> RequestGeneration:
    return create_request_generation()


def get_get_generation_usecase() -> GetGeneration:
    return create_get_generation()


async def run_generate_document(generation_id: UUID) -> None:
    usecase = create_generate_document()
    await usecase.execute(generation_id)


@router.post("", status_code=201, response_model=GenerationCreatedDto)
async def create_generation(
    request: GenerationRequestDto,
    background_tasks: BackgroundTasks,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    usecase: RequestGeneration = Depends(get_request_generation_usecase),
) -> GenerationCreatedDto:
    generation = await usecase.execute(
        topic=request.topic,
        volume_pages=request.volume_pages,
        requirements=request.requirements,
        extra_wishes=request.extra_wishes,
        document_type=request.document_type,
    )
    background_tasks.add_task(run_generate_document, generation.id)
    return GenerationCreatedDto.from_domain(generation)


@router.get("/{generation_id}", response_model=GenerationDetailDto)
async def get_generation(
    generation_id: UUID,
    usecase: GetGeneration = Depends(get_get_generation_usecase),
) -> GenerationDetailDto:
    generation = await usecase.execute(generation_id)
    if generation is None:
        raise HTTPException(status_code=404, detail="generation not found")
    return GenerationDetailDto.from_domain(generation)
