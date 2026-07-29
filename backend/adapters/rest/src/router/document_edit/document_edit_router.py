"""Story 19's seven AI-edit routes.

Every handler is the same shape: take the path identifiers already typed by FastAPI,
take the owner id from the Bearer dependency, and await the route's usecase with
exactly those. The scope guard (`resolve_owned_document`) is the first statement of
each usecase, so the refusal for an absent document and the refusal for a foreign one
are one answer produced in one place, rendered here by the app's
`not_found_exception_handler` as the canonical `{error_code, message}` envelope.

Two shapes are deliberately absent, and either would break scenario 1.1 if introduced:

1. **No Pydantic body model as a handler parameter.** FastAPI validates a declared
   body model *before* the handler body runs, so a malformed `base_version` would be
   answered 422 before the guard is ever reached — disclosing, through the status,
   that the document was reachable enough to have its body inspected. When the request
   payload is needed (scenario 2.x), read it after the guard has answered, or hang
   validation off a dependency ordered behind it.

2. **No `StreamingResponse` around the stream usecase.** The usecase is awaited before
   any response object is constructed; `StreamingResponse(generator())` commits a 200
   `text/event-stream` status line before the generator ever raises, which would turn a
   refusal into an error frame inside an opened stream.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from security.current_owner import get_current_owner_id

router = APIRouter(prefix="/api/v1/documents", tags=["ai-edits"])

_WIRED_BY_COMPOSITION_ROOT = "wired by the application composition root"


def get_queue_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_stream_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_get_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_cancel_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_list_messages_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_list_revisions_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_restore_revision_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


@router.post("/{document_id}/ai-edits")
async def queue_ai_edit(
    document_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_queue_ai_edit_usecase),
) -> Any:
    return await usecase.execute(document_id=document_id, owner_id=owner_id)


@router.get("/{document_id}/ai-edits/{edit_id}/stream")
async def stream_ai_edit(
    document_id: UUID,
    edit_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_stream_ai_edit_usecase),
) -> Any:
    # Awaited, never wrapped: see the module docstring's second constraint.
    return await usecase.execute(document_id=document_id, owner_id=owner_id, edit_id=edit_id)


@router.get("/{document_id}/ai-edits/{edit_id}")
async def get_ai_edit(
    document_id: UUID,
    edit_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_get_ai_edit_usecase),
) -> Any:
    return await usecase.execute(document_id=document_id, owner_id=owner_id, edit_id=edit_id)


@router.post("/{document_id}/ai-edits/{edit_id}/cancel")
async def cancel_ai_edit(
    document_id: UUID,
    edit_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_cancel_ai_edit_usecase),
) -> Any:
    return await usecase.execute(document_id=document_id, owner_id=owner_id, edit_id=edit_id)


@router.get("/{document_id}/messages")
async def list_messages(
    document_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_list_messages_usecase),
) -> Any:
    return await usecase.execute(document_id=document_id, owner_id=owner_id)


@router.get("/{document_id}/revisions")
async def list_revisions(
    document_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_list_revisions_usecase),
) -> Any:
    return await usecase.execute(document_id=document_id, owner_id=owner_id)


@router.post("/{document_id}/revisions/{revision_number}/restore")
async def restore_revision(
    document_id: UUID,
    revision_number: int,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: Any = Depends(get_restore_revision_usecase),
) -> Any:
    return await usecase.execute(
        document_id=document_id, owner_id=owner_id, revision_number=revision_number
    )
