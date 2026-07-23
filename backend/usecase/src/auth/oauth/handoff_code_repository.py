from datetime import datetime
from typing import Protocol
from uuid import UUID

from auth.handoff_code import HandoffCode


class HandoffCodeRepository(Protocol):
    """Persistence for the one-time handoff code that rides in the callback redirect."""

    async def save(self, code: HandoffCode) -> None: ...

    async def redeem(self, value: str, moment: datetime) -> UUID | None:
        """Atomically consume an unexpired code and return its account id, or None.

        The redeem is a single conditional delete: two concurrent exchanges of the
        same code contend for the row lock, exactly one deletes-and-returns, the
        other finds the row gone and returns None. A read-then-delete would let both
        read the row before either deletes it and mint two sessions from one code.
        The `moment > expires_at` guard folds the TTL check into the same statement,
        so an expired code is never redeemable even for an instant.
        """
        ...
