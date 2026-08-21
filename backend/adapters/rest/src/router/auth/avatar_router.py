from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from auth.avatar import AVATAR_TOO_LARGE_CODE, AVATAR_TOO_LARGE_MESSAGE, MAX_AVATAR_BYTES
from auth.delete_avatar import DeleteAvatar
from auth.get_avatar import GetAvatar
from auth.update_avatar import UpdateAvatar
from dto.auth.avatar_response import avatar_response
from dto.auth.profile_response_dto import ProfileResponseDto
from router import api_routes
from security.current_owner import get_current_owner_id
from shared.exceptions import ValidationException

router = APIRouter(prefix=api_routes.AVATAR, tags=["auth"])


def get_update_avatar_usecase() -> UpdateAvatar:
    raise NotImplementedError("wired by the application composition root")


def get_delete_avatar_usecase() -> DeleteAvatar:
    raise NotImplementedError("wired by the application composition root")


def get_get_avatar_usecase() -> GetAvatar:
    raise NotImplementedError("wired by the application composition root")


@router.put("", status_code=200, response_model=ProfileResponseDto)
async def upload_avatar(
    request: Request,
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: UpdateAvatar = Depends(get_update_avatar_usecase),
) -> ProfileResponseDto:
    """Replace the caller's avatar with the raw bytes in the request body.

    NOT multipart. There is exactly one field, so a form part buys nothing and
    costs a multipart parser on an authenticated route that accepts arbitrary
    bytes -- boundary handling, part limits, filename decoding, all of it reached
    before any of our own checks run.

    The client's `Content-Type` is read for the cheap size gate below and for
    nothing else. What the image IS gets decided from its magic bytes, and that
    decision is what gets stored and later served.

    Answers with the full profile so the client refreshes its identity snapshot
    from this response instead of re-hitting `GET /me`.
    """
    _refuse_declared_size_over_the_cap(request)
    return ProfileResponseDto.from_domain(
        await usecase.execute(account_id=owner_id, data=await request.body())
    )


@router.delete("", status_code=200, response_model=ProfileResponseDto)
async def remove_avatar(
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: DeleteAvatar = Depends(get_delete_avatar_usecase),
) -> ProfileResponseDto:
    """Remove the avatar. 200 whether or not there was one.

    Idempotent by contract: the client asked for "no avatar" and that is the
    state it gets. A 404 on the second call would make a retry after a dropped
    response look like a failure.
    """
    return ProfileResponseDto.from_domain(await usecase.execute(account_id=owner_id))


@router.get("")
async def read_avatar(
    owner_id: UUID = Depends(get_current_owner_id),
    usecase: GetAvatar = Depends(get_get_avatar_usecase),
) -> Response:
    """The caller's avatar bytes, served as the type they were proven to be.

    No `response_model`: the body is an image, not JSON. The headers this returns
    are the security half of the contract -- see `avatar_response`.

    404 when there is no avatar (NotFoundException, rendered by the existing
    handler in the canonical envelope). Never 403 and never a 200 with an empty
    body: the latter would be indistinguishable from a broken image to a client.
    """
    return avatar_response(await usecase.execute(account_id=owner_id))


def _refuse_declared_size_over_the_cap(request: Request) -> None:
    """Refuse on Content-Length before the body is read into memory.

    The domain re-checks the ACTUAL length, and that check is the real guard --
    Content-Length is client-supplied and a chunked request carries none. This one
    exists so an oversized upload is refused before the process buffers it, rather
    than after. Same error code as the domain's: to the client it is one refusal.
    """
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > MAX_AVATAR_BYTES:
        raise ValidationException(
            error_code=AVATAR_TOO_LARGE_CODE, message=AVATAR_TOO_LARGE_MESSAGE
        )
