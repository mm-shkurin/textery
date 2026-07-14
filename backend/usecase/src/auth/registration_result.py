from dataclasses import dataclass
from typing import Optional

from auth.account import Account
from auth.verification_code import VerificationCode


@dataclass(frozen=True)
class RegistrationResult:
    account: Account
    verification_code: Optional[VerificationCode]
