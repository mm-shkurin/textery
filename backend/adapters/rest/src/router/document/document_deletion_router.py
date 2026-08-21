"""DELETE /api/v1/documents/{id} — «удалить текст из истории».

Its own module, not another route on `document_router`: that file was at the
200-line cap, and the split follows the precedent the auth slice already set with
`deletion_router`. It carries the same prefix, so the two are one resource on the
wire and the reader of the URL cannot tell they were split.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response

from document.delete_document import DeleteDocument
from router import api_routes
from security.current_owner import get_current_owner_id

router = APIRouter(prefix=api_routes.DOCUMENTS, tags=["documents"])


def get_delete_document_usecase() -> DeleteDocument:
    raise NotImplementedError("wired by the application composition root")


@router.delete("/{document_id}", status_code=204, response_class=Response)
async def delete_document(
    document_id: UUID,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: DeleteDocument = Depends(get_delete_document_usecase),
) -> Response:
    """204 on success, 404 when nothing of the caller's own matched.

    Not idempotent-by-silence: a second DELETE of the same id answers 404 rather
    than 204. The user-facing action is a list row disappearing, and a client
    that treats "already gone" as success would hide a delete aimed at the wrong
    id — the one mistake this endpoint can make that the user cannot undo.

    A foreign document answers 404 too, decided in SQL by the owner predicate:
    the usecase never learns whether the row existed, so the response cannot leak
    it either.

    `Response` with no body rather than `None`: a 204 that carries a JSON `null`
    is a contradiction some proxies and clients handle badly.
    """
    await usecase.execute(document_id=document_id, owner_id=owner_id)
    return Response(status_code=204)
