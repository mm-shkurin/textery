from uuid import UUID

from fastapi import APIRouter, Depends

from auth.delete_account import DeleteAccount
from dto.auth.delete_account_request_dto import DeleteAccountRequestDto
from router import api_routes
from security.current_owner import get_current_owner_id

# POST, not `DELETE /api/v1/auth/me`. The operation needs a confirmation body, and
# a body on DELETE is the thing some proxies, CDNs and HTTP clients drop without
# saying so -- a request that arrives with the confirmation silently missing would
# be answered by the one refusal this endpoint has, and the user would be told
# their password was wrong. A sub-resource that is CREATED ("a deletion") is also
# an honest reading of POST, not a workaround.
router = APIRouter(prefix=api_routes.DELETION, tags=["auth"])


def get_delete_account_usecase() -> DeleteAccount:
    raise NotImplementedError("wired by the application composition root")


@router.post("", status_code=204)
async def delete_account(
    request: DeleteAccountRequestDto | None = None,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: DeleteAccount = Depends(get_delete_account_usecase),
) -> None:
    """Delete the caller's own account, irreversibly, once the confirmation matches.

    The account comes from the token; no route parameter names it, so this cannot
    be pointed at anyone else and there is no ownership check to get wrong.

    The body is optional at this layer so that a request arriving without one
    takes the same DELETION_CONFIRMATION_INVALID path as a wrong password, rather
    than FastAPI's 422 in a different envelope. Which field matters is the
    account's business, not the request's -- see DeleteAccount.

    204 with no body: there is no resource left to describe, and an empty 200
    would invite a client to look for a payload that will never exist.
    """
    confirmation = request or DeleteAccountRequestDto()
    await usecase.execute(
        account_id=owner_id,
        password=confirmation.password,
        confirm_email=confirmation.confirm_email,
    )
