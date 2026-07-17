from uuid import UUID

from auth.verification_code import VerificationCode


class FakeVerificationCodeRepository:
    def __init__(self) -> None:
        self.saved_codes: list[VerificationCode] = []
        self.raise_on_save: Exception | None = None
        self.find_active_by_account_id_call_count = 0

    async def save(self, code: VerificationCode) -> None:
        if self.raise_on_save is not None:
            raise self.raise_on_save
        self.saved_codes.append(code)

    async def find_active_by_account_id(self, account_id: UUID) -> VerificationCode | None:
        # Mirrors SqlAlchemyVerificationCodeRepository: the most recently issued
        # code for the account, with neither expiry nor consumption filtered out.
        # Filtering consumed_at here (as this fake used to) would diverge from the
        # real adapter and hide a replayed code behind the same None the
        # unknown-account path returns.
        self.find_active_by_account_id_call_count += 1
        return next((c for c in reversed(self.saved_codes) if c.account_id == account_id), None)
