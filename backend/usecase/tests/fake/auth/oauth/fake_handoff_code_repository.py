from datetime import datetime
from uuid import UUID

from auth.handoff_code import HandoffCode


class FakeHandoffCodeRepository:
    """In-memory `HandoffCodeRepository`. `redeem` is remove-on-read with the TTL
    folded into the check, mirroring the real single conditional delete: a spent or
    expired code returns None, and a redeemed code is gone for any later caller.
    """

    def __init__(self) -> None:
        self._by_value: dict[str, HandoffCode] = {}
        self.redeem_calls: list[str] = []

    async def save(self, code: HandoffCode) -> None:
        self._by_value[code.value] = code

    async def redeem(self, value: str, moment: datetime) -> UUID | None:
        self.redeem_calls.append(value)
        code = self._by_value.get(value)
        if code is None or code.is_expired_at(moment):
            return None
        del self._by_value[value]
        return code.account_id
