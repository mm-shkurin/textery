from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_eraser import SqlAlchemyAccountEraser
from access.auth.account_storage import SqlAlchemyAccountRepository
from access.auth.avatar_storage import SqlAlchemyAvatarRepository
from access.auth.verification_code_storage import SqlAlchemyVerificationCodeRepository
from auth.delete_account import DeleteAccount
from auth.delete_avatar import DeleteAvatar
from auth.get_avatar import GetAvatar
from auth.get_profile import GetProfile
from auth.login_user import LoginUser
from auth.refresh_access_token import RefreshAccessToken
from auth.register_user import RegisterUser
from auth.rename_account import RenameAccount
from auth.resend_code import ResendCode
from auth.token_service import TokenService
from auth.update_avatar import UpdateAvatar
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


@request_scoped
def create_get_profile(session: AsyncSession) -> GetProfile:
    return GetProfile(account_repository=SqlAlchemyAccountRepository(session))


@request_scoped
def create_rename_account(session: AsyncSession) -> RenameAccount:
    return RenameAccount(
        account_repository=SqlAlchemyAccountRepository(session),
        # A REAL UnitOfWork, on the SAME session the repository holds. Omitting it
        # falls back to NullUnitOfWork, whose commit() returns None without
        # touching the transaction: the UPDATE would be rolled back when
        # request_scoped closes the session, and PATCH would answer 200 with the
        # new name while the database kept the old one. No exception, no log, no
        # failing unit test -- the fakes commit nothing either. That is precisely
        # the defect test_login_wiring.py was written for.
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_update_avatar(session: AsyncSession) -> UpdateAvatar:
    return UpdateAvatar(
        account_repository=SqlAlchemyAccountRepository(session),
        avatar_repository=SqlAlchemyAvatarRepository(session),
        clock=SystemClock(),
        # Same session as both repositories, and a REAL UnitOfWork -- the default
        # NullUnitOfWork commits nothing and would answer 200 with a fresh
        # avatar_updated_at over an unchanged row.
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_delete_avatar(session: AsyncSession) -> DeleteAvatar:
    return DeleteAvatar(
        account_repository=SqlAlchemyAccountRepository(session),
        avatar_repository=SqlAlchemyAvatarRepository(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_delete_account(session: AsyncSession) -> DeleteAccount:
    return DeleteAccount(
        account_repository=SqlAlchemyAccountRepository(session),
        account_eraser=SqlAlchemyAccountEraser(session),
        # The same hasher registration and login use -- the stored hash must be
        # verified by whatever produced it.
        password_hasher=BcryptPasswordHasher(),
        # One UnitOfWork on the SAME session the eraser executes on, so all five
        # DELETEs are one transaction. Wired explicitly because the default
        # NullUnitOfWork commits nothing: the endpoint would answer 204 while the
        # session rolled every DELETE back on close.
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_get_avatar(session: AsyncSession) -> GetAvatar:
    # No UnitOfWork: this one only reads.
    return GetAvatar(avatar_repository=SqlAlchemyAvatarRepository(session))


class _AccountExistence:
    """The `AccountExistence` port over the account repository.

    An adapter of two lines rather than handing the rest layer the repository
    itself: the auth boundary needs one yes/no answer, and a dependency that
    could also read an email or reset a lockout counter invites a route to do it.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._accounts = SqlAlchemyAccountRepository(session)

    async def exists(self, account_id: UUID) -> bool:
        return await self._accounts.find_by_id(account_id) is not None


@request_scoped
def create_account_existence(session: AsyncSession) -> _AccountExistence:
    return _AccountExistence(session)


def create_token_service() -> TokenService:
    """The already-built JWT service, for the rest layer's Bearer dependency.

    Shares the module-level instance with login/refresh rather than building a
    second one: two instances reading the same env var would still agree, but only
    by luck -- and a future per-request build would re-raise the empty-secret
    ValueError on the request path instead of at boot.
    """
    return token_service
