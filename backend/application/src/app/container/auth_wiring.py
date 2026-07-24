from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.login_user import LoginUser
from auth.refresh_access_token import RefreshAccessToken
from auth.register_user import RegisterUser
from auth.resend_code import ResendCode
from auth.token_service import TokenService
from auth.verify_account import VerifyAccount
from container.runtime import request_scoped, token_service
from hashing.bcrypt_password_hasher import BcryptPasswordHasher
from session import SqlAlchemyUnitOfWork
from shared.clock import SystemClock


@request_scoped
def create_register_user(session: AsyncSession) -> RegisterUser:
    return RegisterUser(
        password_hasher=BcryptPasswordHasher(),
        account_repository=SqlAlchemyAccountRepository(session),
        verification_code_repository=SqlAlchemyVerificationCodeRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_login_user(session: AsyncSession) -> LoginUser:
    return LoginUser(
        account_repository=SqlAlchemyAccountRepository(session),
        password_hasher=BcryptPasswordHasher(),
        token_service=token_service,
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_refresh_access_token(session: AsyncSession) -> RefreshAccessToken:
    return RefreshAccessToken(
        account_repository=SqlAlchemyAccountRepository(session),
        token_service=token_service,
    )


@request_scoped
def create_verify_account(session: AsyncSession) -> VerifyAccount:
    return VerifyAccount(
        account_repository=SqlAlchemyAccountRepository(session),
        verification_code_repository=SqlAlchemyVerificationCodeRepository(session),
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_resend_code(session: AsyncSession) -> ResendCode:
    return ResendCode(
        account_repository=SqlAlchemyAccountRepository(session),
        verification_code_repository=SqlAlchemyVerificationCodeRepository(session),
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


def create_token_service() -> TokenService:
    """The already-built JWT service, for the rest layer's Bearer dependency.

    Shares the module-level instance with login/refresh rather than building a
    second one: two instances reading the same env var would still agree, but only
    by luck -- and a future per-request build would re-raise the empty-secret
    ValueError on the request path instead of at boot.
    """
    return token_service
