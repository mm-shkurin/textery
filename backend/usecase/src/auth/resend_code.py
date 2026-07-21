from auth.account_repository import AccountRepository
from auth.verification_code_repository import VerificationCodeRepository
from shared.clock import Clock
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class ResendCode:
    """Resend a verification code for a pending account (scenario 4.x).

    A NEW top-level usecase, not a method on VerifyAccount: resend is a distinct
    register-like issuance gated by a cooldown, so per the usecase-interaction rule
    it is its own entry point, sharing only domain-level code generation with
    registration. Reuses the same ports RegisterUser/VerifyAccount depend on
    (AccountRepository, VerificationCodeRepository, Clock, UnitOfWork).

    RED scaffolding only: the cooldown gate and insert-only supersession are
    implemented at green-usecase. execute() is intentionally unimplemented so the
    red-usecase FakeClock test fails on the not-yet-built behavior.
    """

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

    async def execute(self, email: str) -> None:
        raise NotImplementedError()
