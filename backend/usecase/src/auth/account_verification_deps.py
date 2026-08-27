"""The port preamble shared by the account-verification usecases.

`VerifyAccount` and `ResendCode` are separate top-level usecases -- neither calls
the other -- but they hold exactly the same four collaborators, and two hand-copied
constructors is how one of them ends up quietly defaulting a UnitOfWork the other
does not. This base is NOT a usecase: it has no `execute` and is never wired or called as
one. It exists so the things both usecases need are written once, in the same
layer: the four collaborators, and the two refusals below.

The refusals live here because they are one CONTRACT, not two implementations of
it. `auth_verify.yaml` and the resend route answer the same two codes for the same
two situations, and two hand-copied factories are how one of them quietly drifts —
a reworded message or a changed code on one route only, which no test comparing a
route against itself would catch.
"""

from auth.account_repository import AccountRepository
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock
from shared.error_codes import ErrorCode
from shared.exceptions import ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class AccountVerificationDependencies:
    """Holds the four ports an account-verification usecase needs."""

    def __init__(
        self,
        account_repository: AccountRepository,
        verification_code_repository: VerificationCodeRepository,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self._account_repository = account_repository
        self._verification_code_repository = verification_code_repository
        self._clock = clock
        self._unit_of_work = unit_of_work or NullUnitOfWork()

    def _already_verified(self) -> ValidationException:
        """The account is already verified, and the request is not the idempotent one.

        Distinct from `_invalid_or_expired`: on an already-verified account the
        transition is done, so a code that is not the one that verified it — or a
        resend asked for at all — is a genuine conflict, not a state-hiding oracle.
        The matching code takes the idempotent-success path in `VerifyAccount` and
        never reaches here.
        """
        return ValidationException(
            error_code=ErrorCode.ALREADY_VERIFIED,
            message="The account is already verified.",
        )

    def _invalid_or_expired(self) -> ValidationException:
        """One generic rejection for every failure that depends on stored state.

        Wrong code, no such account, and no issued code all answer identically, on
        purpose: `auth_verify.yaml` requires the 400 to be client-safe and to not
        reveal whether the email exists. Giving the unknown-account case its own
        code (or letting it 500 on a None dereference, which is what happened
        before this) turns the status line into an account-existence oracle.

        Distinct from `INVALID_CODE`, which is shape-only: that one is a pure
        function of the submitted string and reveals nothing about any account.

        Known gap, not closed here: the unknown-account branch returns after one
        query while a wrong code costs two, so the paths are still distinguishable
        by timing. Out of scope for this sprint.
        """
        return ValidationException(
            error_code=ErrorCode.INVALID_OR_EXPIRED_CODE,
            message="The verification code is invalid or has expired.",
        )
