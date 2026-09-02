"""GET /api/v1/documents — the caller's own document history.

Its own module, not another route on `document_router`: that file sat exactly at
the 200-line cap with no headroom, so the next route added to it forced a split
under time pressure rather than by design. Same precedent, same prefix, and the
same consequence for ordering as `document_deletion_router` — see below.

Every query parameter here arrives as raw `str | None`, `limit` included. A
`datetime` or an `int` annotation would answer a malformed value in Pydantic's
envelope rather than this API's `{error_code, message}`, which is the one shape
every other refusal in this API uses. The filters are parsed by the domain and
`limit` is range-checked by the domain's `PageRequest`, so `?limit=abc` and
`?limit=999` answer alike.

This router must be registered BEFORE any router carrying a parameterised
`/{document_id}` route on the same prefix. `""` and `/{id}` are distinct paths to
Starlette either way, but keeping the literal above the parameterised one is the
habit that stops a future `/documents/recent` from being swallowed.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from document.document_filter import DocumentFilter
from document.list_documents import ListDocuments
from dto.document.document_summary_dto import DocumentSummaryDto
from dto.shared.page_dto import PageDto
from dto.shared.query_int import exact_int
from router import api_routes
from security.current_owner import get_current_owner_id
from shared.page import DEFAULT_LIMIT

router = APIRouter(prefix=api_routes.DOCUMENTS, tags=["documents"])


def get_list_documents_usecase() -> ListDocuments:
    raise NotImplementedError("wired by the application composition root")


@router.get("", response_model=PageDto[DocumentSummaryDto])
async def list_documents(
    limit: str | None = None,
    cursor: str | None = None,
    q: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: ListDocuments = Depends(get_list_documents_usecase),
) -> PageDto[DocumentSummaryDto]:
    """The caller's own document history, newest first."""
    document_filter = DocumentFilter.parse(q=q, created_from=created_from, created_to=created_to)
    page = await usecase.execute(
        owner_id=owner_id,
        limit=exact_int(limit, DEFAULT_LIMIT, "INVALID_LIMIT", "limit"),
        cursor=cursor,
        document_filter=document_filter,
    )
    return PageDto[DocumentSummaryDto](
        items=[DocumentSummaryDto.from_domain(document) for document in page.items],
        next_cursor=page.next_cursor,
    )
