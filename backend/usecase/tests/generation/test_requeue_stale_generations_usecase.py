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


class TestSweepSurvivesContention:
    """A row lost to another replica must not abort the batch.

    The sweep runs in every replica's lifespan and claims rows through a
    compare-and-swap, so exactly one instance wins each contested row and the
    others are told they lost. That is the design working, not a failure -- but
    an escaping exception aborted the whole loop at the first contested row,
    stranding every later one for another interval and surfacing as "stale
    generation sweep failed" in the lifespan logger.
    """

    async def test_should_requeue_the_rest_when_one_row_is_claimed_by_another_replica(
        self, requeue_stale_generations_statements: RequeueStaleGenerationsStatements
    ):
        lost = requeue_stale_generations_statements.given_stale_pending_generation()
        still_ours = requeue_stale_generations_statements.given_stale_pending_generation()
        requeue_stale_generations_statements.given_row_already_claimed_by_another_replica(lost)

        await requeue_stale_generations_statements.sweep_stale_generations()

        # The contested row is not reported as requeued -- the application layer
        # re-triggers generation for whatever comes back, and re-triggering a row
        # another replica already owns is the duplicate paid LLM call the CAS
        # exists to prevent.
        requeue_stale_generations_statements.assert_requeued(still_ours)

    async def test_should_requeue_the_rest_when_one_row_was_deleted(
        self, requeue_stale_generations_statements: RequeueStaleGenerationsStatements
    ):
        gone = requeue_stale_generations_statements.given_stale_pending_generation()
        still_ours = requeue_stale_generations_statements.given_stale_pending_generation()
        requeue_stale_generations_statements.given_row_deleted_before_the_sweep_reached_it(gone)

        await requeue_stale_generations_statements.sweep_stale_generations()

        requeue_stale_generations_statements.assert_requeued(still_ours)
