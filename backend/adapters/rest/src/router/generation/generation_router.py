from fastapi import APIRouter, Depends, Header

from dto.generation.generation_request_dto import GenerationRequestDto
from generation.request_generation import RequestGeneration

router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


def get_generation_usecase() -> RequestGeneration:
    return RequestGeneration()


@router.post("", status_code=201)
async def create_generation(
    request: GenerationRequestDto,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    usecase: RequestGeneration = Depends(get_generation_usecase),
) -> None:
    await usecase.execute(
        topic=request.topic,
        volume_pages=request.volume_pages,
        requirements=request.requirements,
        extra_wishes=request.extra_wishes,
        document_type=request.document_type,
    )
