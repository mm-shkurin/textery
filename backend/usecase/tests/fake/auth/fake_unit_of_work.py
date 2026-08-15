class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commit_call_count = 0
        # Every commit() entry, counted BEFORE raise_on_commit fires -- so a test can
        # prove a commit was ATTEMPTED even when it blows up (commit_call_count only
        # counts commits that succeeded past the raise). Scenario 5.4 reset-swallow.
        self.commit_attempt_count = 0
        self.rollback_call_count = 0
        self.raise_on_commit: Exception | None = None
        self.raise_on_rollback: Exception | None = None
        # Shared with a Fake repo (both assigned the same list) so a test can pin
        # the RELATIVE order of a repo write vs the commit (scenario 5.3:
        # increment -> commit -> raise). Left None so existing Statements pay nothing.
        self.call_log: list[str] | None = None
        # Callables run on rollback(), so a Fake that accumulated writes can undo
        # them the way the real transaction would. Without this a test can only
        # prove rollback was CALLED, never that it took anything back -- and
        # "rollback was called" is exactly what a half-deleted account would also
        # report. Empty by default, so existing Statements pay nothing.
        self.rollback_hooks: list = []

    async def commit(self) -> None:
        self.commit_attempt_count += 1
        if self.raise_on_commit is not None:
            raise self.raise_on_commit
        self.commit_call_count += 1
        if self.call_log is not None:
            self.call_log.append("commit")

    async def rollback(self) -> None:
        self.rollback_call_count += 1
        if self.raise_on_rollback is not None:
            raise self.raise_on_rollback
        for undo in self.rollback_hooks:
            undo()
