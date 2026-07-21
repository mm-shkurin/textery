from datetime import datetime
from uuid import UUID

from auth.verification_code import VerificationCode


class FakeVerificationCodeRepository:
    def __init__(self) -> None:
        self.saved_codes: list[VerificationCode] = []
        self.raise_on_save: Exception | None = None
        self.find_active_by_account_id_call_count = 0
        self.transition_to_consumed_calls: list[tuple[UUID, datetime]] = []

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

    async def transition_to_consumed(self, code_id: UUID, now: datetime) -> bool:
        # Spy + real semantics, mirroring the atomic conditional UPDATE the db
        # adapter runs: the first caller stamps consumed_at and gets True; a later
        # caller finds it already consumed and gets False with no re-stamp. The
        # recorded (code_id, now) is what the usecase test asserts on, so a
        # regression back to consume()+save() -- which never calls this -- leaves
        # the list empty and goes RED.
        self.transition_to_consumed_calls.append((code_id, now))
        code = next((c for c in reversed(self.saved_codes) if c.id == code_id), None)
        if code is None or code.consumed_at is not None:
            return False
        code.consume(now)
        return True
