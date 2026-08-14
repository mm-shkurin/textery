from uuid import UUID


class FakeAccountEraser:
    """In-memory `AccountEraser` double.

    `erase_after_children_removed` is the lever that matters: it removes the
    account's children, then fails, which is the one failure mode
    `SqlAlchemyAccountEraser` can genuinely hit halfway through. A test uses it to
    prove the usecase rolls the WHOLE removal back -- a caller left with an
    account and no documents is the irreversible outcome nobody can undo.
    """

    def __init__(self) -> None:
        self.erase_calls: list[UUID] = []
        self.raise_on_erase: Exception | None = None
        self.erase_after_children_removed: Exception | None = None
        # Rows this eraser has removed, in order. A rollback empties it, exactly as
        # the real transaction would.
        self.removed_rows: list[str] = []
        self.child_rows = ("documents", "generations", "verification_codes")
        self.call_log: list[str] | None = None

    async def erase(self, account_id: UUID) -> None:
        self.erase_calls.append(account_id)
        if self.call_log is not None:
            self.call_log.append("erase")
        if self.raise_on_erase is not None:
            raise self.raise_on_erase
        self.removed_rows.extend(self.child_rows)
        if self.erase_after_children_removed is not None:
            # Children are gone from this transaction's point of view and the
            # account row is not. Exactly the half-done state a rollback exists for.
            raise self.erase_after_children_removed
        self.removed_rows.append("accounts")
