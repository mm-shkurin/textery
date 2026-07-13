from statements.requeue_stale_generations_statements import RequeueStaleGenerationsStatements


class TestRequeueStalePending:
    """A pending generation stuck past the staleness threshold is reset to pending
    so the application layer can retrigger execution after a worker crash."""

    async def test_should_requeue_stale_pending_generation(
        self, requeue_stale_generations_statements: RequeueStaleGenerationsStatements
    ):
        generation = requeue_stale_generations_statements.given_stale_pending_generation()
        await requeue_stale_generations_statements.sweep_stale_generations()
        requeue_stale_generations_statements.assert_requeued(generation)
        requeue_stale_generations_statements.assert_status_reset_to_pending(generation)


class TestRequeueStaleInProgress:
    """An in_progress generation stuck past the staleness threshold (worker died
    mid-execution) is reset to pending too."""

    async def test_should_requeue_stale_in_progress_generation(
        self, requeue_stale_generations_statements: RequeueStaleGenerationsStatements
    ):
        generation = requeue_stale_generations_statements.given_stale_in_progress_generation()
        await requeue_stale_generations_statements.sweep_stale_generations()
        requeue_stale_generations_statements.assert_requeued(generation)
        requeue_stale_generations_statements.assert_status_reset_to_pending(generation)


class TestSkipFreshPending:
    """A pending generation still within the staleness threshold is left alone —
    it may just be executing normally."""

    async def test_should_not_requeue_fresh_pending_generation(
        self, requeue_stale_generations_statements: RequeueStaleGenerationsStatements
    ):
        requeue_stale_generations_statements.given_fresh_pending_generation()
        await requeue_stale_generations_statements.sweep_stale_generations()
        requeue_stale_generations_statements.assert_nothing_requeued()


class TestSkipCompleted:
    """A completed generation is never requeued regardless of age."""

    async def test_should_not_requeue_completed_generation(
        self, requeue_stale_generations_statements: RequeueStaleGenerationsStatements
    ):
        requeue_stale_generations_statements.given_completed_generation()
        await requeue_stale_generations_statements.sweep_stale_generations()
        requeue_stale_generations_statements.assert_nothing_requeued()
