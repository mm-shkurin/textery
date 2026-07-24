from dataclasses import dataclass

from auth.account import Account
from auth.verification_code import VerificationCode


@dataclass(frozen=True)
class RegistrationResult:
    """What a completed registration hands back: the account and its first code.

    `verification_code` is **not** optional. RegisterUser builds this only after
    the code is generated and committed -- a registration that failed to persist
    one raises instead of returning a half-result. The `| None` this field used to
    carry described a state the code never produces, and its only effect was to
    make RegisterResponseDto read `.code` off a value the type said might be None.
    """

    account: Account
    verification_code: VerificationCode
