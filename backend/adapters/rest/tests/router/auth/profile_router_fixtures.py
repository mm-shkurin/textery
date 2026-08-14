"""One app carrying the three `/auth/me` routers, with the token boundary stubbed.

The doubles are local to the rest layer on purpose: these tests are about what
the HTTP surface does with what a usecase returns -- statuses, headers, the shape
of the body -- and importing the usecase suite's fakes would drag its arrangement
in with them.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from middleware.no_store import NoStoreMiddleware

from auth.account import Account
from auth.avatar_repository import StoredAvatar
from error_handling.exception_handlers import (
    not_found_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from router.auth import avatar_router, deletion_router, profile_router
from security.current_owner import get_current_owner_id
from shared.exceptions import NotFoundException, ValidationException

OWNER_ID = UUID("11111111-2222-3333-4444-555555555555")
EMAIL = "ada@example.ru"
CREATED_AT = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
AVATAR_UPDATED_AT = datetime(2026, 8, 14, 12, 0, 0, 123456, tzinfo=UTC)


def an_account(
    name: str | None = None,
    avatar_updated_at: datetime | None = None,
    password_hash: str = "hashed::Str0ng!Pass",
) -> Account:
    return Account.reconstitute(
        id=OWNER_ID,
        email=EMAIL,
        password_hash=password_hash,
        created_at=CREATED_AT,
        is_verified=True,
        name=name,
        avatar_updated_at=avatar_updated_at,
    )


def a_stored_avatar(data: bytes, media_type: str, updated_at=AVATAR_UPDATED_AT) -> StoredAvatar:
    return StoredAvatar(data=data, media_type=media_type, updated_at=updated_at)


class RecordingUsecase:
    """Returns `result`, or raises it, and remembers what it was called with."""

    def __init__(self, result=None) -> None:
        self.result = result
        self.calls: list[dict] = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    @property
    def last_call(self) -> dict:
        assert self.calls, "expected the route to have called this usecase"
        return self.calls[-1]


PROVIDERS = {
    "get_profile": profile_router.get_get_profile_usecase,
    "rename_account": profile_router.get_rename_account_usecase,
    "update_avatar": avatar_router.get_update_avatar_usecase,
    "delete_avatar": avatar_router.get_delete_avatar_usecase,
    "get_avatar": avatar_router.get_get_avatar_usecase,
    "delete_account": deletion_router.get_delete_account_usecase,
}


def build_app(**usecases) -> FastAPI:
    """`build_app(get_profile=RecordingUsecase(an_account()))` and so on."""
    app = FastAPI()
    app.add_middleware(NoStoreMiddleware)
    app.include_router(profile_router.router)
    app.include_router(avatar_router.router)
    app.include_router(deletion_router.router)
    # See main.py: Starlette types every handler as taking `Exception`; these take
    # the exception they are registered for. Suppressed per line rather than
    # widening the handlers to satisfy the stub.
    app.add_exception_handler(ValidationException, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(NotFoundException, not_found_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.dependency_overrides[get_current_owner_id] = lambda: OWNER_ID
    for name, usecase in usecases.items():
        app.dependency_overrides[PROVIDERS[name]] = _provider(usecase)
    return app


def _provider(usecase):
    """A zero-argument provider.

    Deliberately NOT `lambda usecase=usecase: usecase`: FastAPI reads a
    dependency's signature, and a parameter with a default becomes a QUERY
    PARAMETER it tries to resolve from the request -- so the override would hand
    the route something other than the object the test is holding, and the spy
    would record nothing while the response still looked right.
    """

    def provide():
        return usecase

    return provide
