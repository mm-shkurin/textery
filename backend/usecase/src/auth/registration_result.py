from dataclasses import dataclass

from auth.account import Account
from auth.verification_code import VerificationCode


@dataclass(frozen=True)
class RegistrationResult:
    account: Account
    verification_code: VerificationCode | None
