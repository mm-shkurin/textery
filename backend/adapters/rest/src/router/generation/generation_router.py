"""Routes for generation requests, retries, and the generation history.

**`POST /{generation_id}/retry`** — «Повторить», re-running a failed generation
from its own stored parameters. The body is OPTIONAL and carries at most the two
values a user re-chooses at the moment of a retry — the register and the length.
Everything else is copied from the source row, so there is no `owner_id`,
`status` or timestamp for a client to over-bind. The header carries the remaining
client-supplied value, and it is validated in the domain rather than as a
`Header(max_length=...)` so a violation answers in this API's
`{error_code, message}` shape.

A replayed key returns the row the first attempt created and starts nothing: the
usecase says whether THIS call created the retry, and only a created one is
enqueued. Enqueuing on the replay path would run the work twice, which is what
the key exists to prevent.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request

from analytics.client_context import visitor_id_of
from dto.generation.generation_request_dto import (
    GenerationRequestDto,
    RetryGenerationRequestDto,
)
from dto.generation.generation_response_dto import (
    GenerationCreatedDto,
    GenerationDetailDto,
    GenerationSummaryDto,
)
from dto.shared.page_dto import PageDto
from dto.shared.query_int import exact_int
from generation.document_generator import DocumentGenerator
from generation.get_generation import GetGeneration
from generation.list_generations import ListGenerations
from generation.request_generation import RequestGeneration
from generation.retry_generation import RetryGeneration
from router import api_routes
from security.current_owner import get_current_owner_id
from shared.exceptions import NotFoundException
from shared.page import DEFAULT_LIMIT

router = APIRouter(prefix=api_routes.GENERATIONS, tags=["generations"])


def get_request_generation_usecase() -> RequestGeneration:
    raise NotImplementedError("wired by the application composition root")


def get_get_generation_usecase() -> GetGeneration:
    raise NotImplementedError("wired by the application composition root")


def get_generate_document_usecase() -> DocumentGenerator:
    raise NotImplementedError("wired by the application composition root")


def get_list_generations_usecase() -> ListGenerations:
    raise NotImplementedError("wired by the application composition root")


def get_retry_generation_usecase() -> RetryGeneration:
    raise NotImplementedError("wired by the application composition root")


@router.get("", response_model=PageDto[GenerationSummaryDto])
async def list_generations(
    limit: str | None = None,
    cursor: str | None = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ListGenerations = Depends(get_list_generations_usecase),
) -> PageDto[GenerationSummaryDto]:
    """The caller's own generation history, newest first.

    `limit` arrives as raw text and `cursor` as-is, not as Query(ge=..., le=...):
    a Pydantic annotation refuses a bad value in ITS envelope, and this contract's
    400s are {error_code, message} -- the same reason IdempotencyKey is not a
    Header constraint. Parsing is transport work and happens here; the bounds stay
    in the domain's PageRequest, shared by every history list.
    """
    page = await usecase.execute(
        owner_id=owner_id,
        limit=exact_int(limit, DEFAULT_LIMIT, "INVALID_LIMIT", "limit"),
        cursor=cursor,
    )
    return PageDto[GenerationSummaryDto](
        items=[GenerationSummaryDto.from_domain(generation) for generation in page.items],
        next_cursor=page.next_cursor,
    )


@router.post("", status_code=201, response_model=GenerationCreatedDto)
async def create_generation(
    request: GenerationRequestDto,
    http_request: Request,
    background_tasks: BackgroundTasks,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: RequestGeneration = Depends(get_request_generation_usecase),
    generate_document: DocumentGenerator = Depends(get_generate_document_usecase),
) -> GenerationCreatedDto:
    generation = await usecase.execute(
        owner_id=owner_id,
        topic=request.topic,
        volume_pages=request.volume_pages,
        requirements=request.requirements,
        extra_wishes=request.extra_wishes,
        document_type=request.document_type,
        text_style=request.text_style,
        # From the `X-Visitor-Id` header, never from the body: the request
        # contract of this endpoint is unchanged by Story 14, and a browser that
        # sends no header simply has no visitor recorded.
        visitor_id=visitor_id_of(http_request),
    )
    background_tasks.add_task(generate_document.execute, generation.id, generation.owner_id)
    return GenerationCreatedDto.from_domain(generation)


@router.post("/{generation_id}/retry", status_code=201, response_model=GenerationCreatedDto)
async def retry_generation(
    generation_id: UUID,
    background_tasks: BackgroundTasks,
    # Optional body, so the plain «Повторить» stays a bodiless POST and only the
    # «в другом стиле» variant sends anything at all.
    request: RetryGenerationRequestDto | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: RetryGeneration = Depends(get_retry_generation_usecase),
    generate_document: DocumentGenerator = Depends(get_generate_document_usecase),
) -> GenerationCreatedDto:
    """«Повторить» — re-run a failed generation. See the module docstring."""
    text_style, volume_pages = _retry_overrides(request)
    retry, created = await usecase.execute(
        generation_id=generation_id,
        owner_id=owner_id,
        idempotency_key=idempotency_key,
        text_style=text_style,
        volume_pages=volume_pages,
    )
    if created:
        # Only a created retry is enqueued: a replayed key returns the row the
        # first attempt created and starts nothing, which is what the key exists
        # to prevent.
        background_tasks.add_task(generate_document.execute, retry.id, retry.owner_id)
    return GenerationCreatedDto.from_domain(retry)


def _retry_overrides(
    request: RetryGenerationRequestDto | None,
) -> tuple[str | None, int | None]:
    """The at-most-two values a user re-chooses at the moment of a retry."""
    if request is None:
        return None, None
    return request.text_style, request.volume_pages


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
        #
        # NotFoundException, not HTTPException: the shared handler is what keeps
        # this in the API's {error_code, message} shape and keeps the resource kind
        # out of the body. Raising HTTPException here would opt this one endpoint
        # out of both.
        raise NotFoundException(f"generation {generation_id} not found")
    return GenerationDetailDto.from_domain(generation)
