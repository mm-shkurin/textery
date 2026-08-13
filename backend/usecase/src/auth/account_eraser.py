from typing import Protocol
from uuid import UUID


class AccountEraser(Protocol):
    """Removes an account and everything that belongs to it.

    One method, not five: the order the rows must go in is a property of the
    schema's foreign keys, so it belongs in the adapter that knows the schema, and
    a port that exposed `delete_documents` / `delete_account` separately would let
    a caller run half of it.

    A port of its own rather than methods on `AccountRepository`, for the same
    reason `AvatarRepository` is separate: this is the only irreversible operation
    in the product, and it should not sit one autocomplete away from
    `find_by_email` in a repository every usecase already holds.
    """

    async def erase(self, account_id: UUID) -> None: ...
