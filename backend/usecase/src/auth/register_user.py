import logging
import unicodedata
from datetime import datetime
from uuid import uuid4

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.email import Email
from auth.email_validation import validate_email
from auth.password import Password
from auth.password_hasher import PasswordHasher
from auth.registration_result import RegistrationResult
from auth.verification_code import VerificationCode
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock, SystemClock
from shared.exceptions import ConflictException, RegistrationFailedException, ValidationException
from shared.rollback import rollback_quietly
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

logger = logging.getLogger(__name__)


class RegisterUser:
    REGISTRATION_FAILED_MESSAGE = (
        "Registration could not be completed due to an unexpected error. Please try again."
    )

    def __init__(
        self,
        password_hasher: PasswordHasher,
        account_repository: AccountRepository,
        verification_code_repository: VerificationCodeRepository,
        clock: Clock | None = None,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        # All three collaborators are required, deliberately without a null-object
        # fallback. A defaulted hasher would persist credentials in the clear; a
        # defaulted repository would drop the entity and let register answer 201,
        # with a verification code, for an account that was never written. Both
        # failures pass every test that does not check storage.
        self.password_hasher = password_hasher
        self.account_repository = account_repository
        self.verification_code_repository = verification_code_repository
        self.clock = clock or SystemClock()
        self.unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, email: str, password: str, confirm_password: str) -> RegistrationResult:
        email_value_object = validate_email(email)
        password_value_object = self._validate_password(password, confirm_password)
        created_at = self.clock.now()
        account = await self._create_and_save_account(
            email_value_object, password_value_object, created_at
        )
        verification_code = VerificationCode.generate(
            id=uuid4(),
            account_id=account.id,
            created_at=created_at,
        )
        await self._save_verification_code_and_commit(verification_code)
        return RegistrationResult(account=account, verification_code=verification_code)

    def _validate_password(self, password: str, confirm_password: str) -> Password:
        try:
            password_value_object = Password(password)
        except ValueError as error:
            raise ValidationException(
                error_code="INVALID_PASSWORD",
                message="The password does not meet the password policy.",
            ) from error
        if password_value_object.value != unicodedata.normalize("NFC", confirm_password):
            raise ValidationException(
                error_code="PASSWORD_MISMATCH",
                message="The password confirmation does not match.",
            )
        return password_value_object

    async def _create_and_save_account(
        self, email_value_object: Email, password_value_object: Password, created_at: datetime
    ) -> Account:
        account = Account.create(
            id=uuid4(),
            email=email_value_object.value,
            password_hash=self.password_hasher.hash(password_value_object.value),
            created_at=created_at,
        )
        try:
            await self.account_repository.save(account)
        except ConflictException as error:
            await rollback_quietly(self.unit_of_work)
            raise ValidationException(
                error_code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email address already exists.",
            ) from error
        except Exception as error:
            # Logged before it is swallowed: the client gets a deliberately vague
            # "please try again", so without this line a programmer error here --
            # a TypeError in Account.create, an AttributeError in the hasher --
            # would be indistinguishable from a genuine storage outage, and both
            # would be invisible.
            logger.exception("registration failed while saving the account")
            await rollback_quietly(self.unit_of_work)
            raise RegistrationFailedException(message=self.REGISTRATION_FAILED_MESSAGE) from error
        return account

    async def _save_verification_code_and_commit(self, verification_code: VerificationCode) -> None:
        try:
            await self.verification_code_repository.save(verification_code)
            await self.unit_of_work.commit()
        except Exception as error:
            logger.exception("registration failed while saving the verification code")
            await rollback_quietly(self.unit_of_work)
            raise RegistrationFailedException(message=self.REGISTRATION_FAILED_MESSAGE) from error
