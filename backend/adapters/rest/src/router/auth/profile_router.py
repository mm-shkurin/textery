from uuid import UUID

from fastapi import APIRouter, Depends

from auth.get_profile import GetProfile
from auth.rename_account import RenameAccount
from dto.auth.profile_response_dto import ProfileResponseDto
from dto.auth.update_profile_request_dto import UpdateProfileRequestDto
from router import api_routes
from security.current_owner import get_current_owner_id

# The same prefix auth_router carries, in a file of its own only because the
# 200-line cap applies per file. Two operations on ONE path: no /auth/profile
# alongside /auth/me, no POST /auth/me/name, and no re-GET after a rename --
# PATCH answers with the full profile so the client refreshes its identity
# snapshot from the response it already has.
router = APIRouter(prefix=api_routes.AUTH, tags=["auth"])


def get_get_profile_usecase() -> GetProfile:
    raise NotImplementedError("wired by the application composition root")


def get_rename_account_usecase() -> RenameAccount:
    raise NotImplementedError("wired by the application composition root")


@router.get("/me", status_code=200, response_model=ProfileResponseDto)
async def read_profile(
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: GetProfile = Depends(get_get_profile_usecase),
) -> ProfileResponseDto:
    """The caller's own profile.

    The account is resolved from the Bearer token and is never a path or query
    parameter -- which is why this route has no 404: it accepts no identifier, so
    there is nothing to enumerate and no ownership check to get wrong. A
    structurally valid token whose row is gone answers 401 like a forged one.

    `Cache-Control: no-store` is NOT set here. It is stamped by
    `NoStoreMiddleware` for every response on this path, including the 401 the
    dependency above raises before this body runs -- see `middleware/no_store.py`.
    """
    return ProfileResponseDto.from_domain(await usecase.execute(account_id=owner_id))


@router.patch("/me", status_code=200, response_model=ProfileResponseDto)
async def update_profile(
    request: UpdateProfileRequestDto,
    owner_id: UUID = Depends(get_current_owner_id),
    read_usecase: GetProfile = Depends(get_get_profile_usecase),
    rename_usecase: RenameAccount = Depends(get_rename_account_usecase),
) -> ProfileResponseDto:
    """Set or clear the display name; answer with the whole profile either way.

    An omitted `name` key takes the read path, not the write path: `{}` means
    "change nothing", so it must not reach an UPDATE. That is fail-closed by
    design -- when a second writable field arrives, a client that sends only the
    field it changed must not erase the other one.

    Two usecases behind one route, and this is NOT a usecase calling a usecase:
    the router picks ONE of them per request, which is the rest -> usecase
    direction the layering rule allows. Both are top-level operations in their own
    right; neither composes the other.

    The response is the profile AFTER normalization, never an echo of the request:
    an NFD body comes back canonically equivalent but not byte-equal, and a
    trailing space comes back trimmed.
    """
    if not request.has_name():
        return ProfileResponseDto.from_domain(await read_usecase.execute(account_id=owner_id))
    account = await rename_usecase.execute(account_id=owner_id, name=request.name)
    return ProfileResponseDto.from_domain(account)
