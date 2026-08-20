"""The port preamble shared by the account-verification usecases.

`VerifyAccount` and `ResendCode` are separate top-level usecases -- neither calls
the other -- but they hold exactly the same four collaborators, and two hand-copied
constructors is how one of them ends up quietly defaulting a UnitOfWork the other
does not. This base is NOT a usecase: it has no `execute`, declares no behaviour,
and exists only so the shared wiring is written once, in the same layer.
"""

from auth.account_repository import AccountRepository
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock
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
        self.account_repository = account_repository
        self.verification_code_repository = verification_code_repository
        self.clock = clock
        self.unit_of_work = unit_of_work or NullUnitOfWork()
