from collections.abc import AsyncIterator

from hashing.bcrypt_password_hasher import BcryptPasswordHasher

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.login_user import LoginUser
from auth.refresh_access_token import RefreshAccessToken
from auth.register_user import RegisterUser
from auth.token_service import TokenService
from auth.verify_account import VerifyAccount
from container.runtime import session_factory, token_service
from session import SqlAlchemyUnitOfWork
from shared.clock import SystemClock


async def create_register_user() -> AsyncIterator[RegisterUser]:
    session = session_factory()
    try:
        yield RegisterUser(
            password_hasher=BcryptPasswordHasher(),
            account_repository=SqlAlchemyAccountRepository(session),
            verification_code_repository=SqlAlchemyVerificationCodeRepository(session),
            unit_of_work=SqlAlchemyUnitOfWork(session),
        )
    finally:
        await session.close()


async def create_login_user() -> AsyncIterator[LoginUser]:
    session = session_factory()
    try:
        yield LoginUser(
            account_repository=SqlAlchemyAccountRepository(session),
            password_hasher=BcryptPasswordHasher(),
            token_service=token_service,
        )
    finally:
        await session.close()


async def create_refresh_access_token() -> AsyncIterator[RefreshAccessToken]:
    session = session_factory()
    try:
        yield RefreshAccessToken(
            account_repository=SqlAlchemyAccountRepository(session),
            token_service=token_service,
        )
    finally:
        await session.close()


async def create_verify_account() -> AsyncIterator[VerifyAccount]:
    session = session_factory()
    try:
        yield VerifyAccount(
            account_repository=SqlAlchemyAccountRepository(session),
            verification_code_repository=SqlAlchemyVerificationCodeRepository(session),
            clock=SystemClock(),
            unit_of_work=SqlAlchemyUnitOfWork(session),
        )
    finally:
        await session.close()


def create_token_service() -> TokenService:
    """The already-built JWT service, for the rest layer's Bearer dependency.

    Shares the module-level instance with login/refresh rather than building a
    second one: two instances reading the same env var would still agree, but only
    by luck -- and a future per-request build would re-raise the empty-secret
    ValueError on the request path instead of at boot.
    """
    return token_service
