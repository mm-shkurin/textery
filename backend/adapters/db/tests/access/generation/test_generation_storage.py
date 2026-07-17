from statements.generation_storage_statements import GenerationStorageStatements


class TestSaveAndGet:
    """A saved generation can be fetched back by id and owner with all fields intact."""

    async def test_should_round_trip_saved_generation(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        generation = generation_storage_statements.build_pending_generation()
        await generation_storage_statements.save_generation(generation)
        await generation_storage_statements.fetch_by_saved_id()
        generation_storage_statements.assert_fetched_matches_saved()


class TestGetUnknownId:
    """Fetching an id that was never saved returns None."""

    async def test_should_return_none_for_unknown_id(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        await generation_storage_statements.fetch_unknown_generation()
        generation_storage_statements.assert_fetched_is_none()


class TestGetForeignOwner:
    """A generation belonging to another account is withheld -- the ownership
    predicate is in the WHERE clause, so a foreign row is indistinguishable from an
    absent one. This is the read half of the IDOR that shipped anonymously."""

    async def test_should_return_none_for_generation_owned_by_someone_else(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        generation = generation_storage_statements.build_pending_generation()
        await generation_storage_statements.save_generation(generation)
        await generation_storage_statements.fetch_saved_generation_as_another_owner()
        generation_storage_statements.assert_fetched_is_none()


class TestUpdate:
    """Updating a saved generation persists its new status and content."""

    async def test_should_persist_status_and_content_after_update(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        generation = generation_storage_statements.build_pending_generation()
        await generation_storage_statements.save_generation(generation)
        generation.complete("Готовый доклад")
        await generation_storage_statements.update_generation(generation)
        await generation_storage_statements.fetch_by_saved_id()
        generation_storage_statements.assert_fetched_status_and_content("completed", "Готовый доклад")


class TestUpdateUnknownId:
    """Updating an id that was never saved raises NotFoundException instead of crashing."""

    async def test_should_raise_not_found_for_unknown_id(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        await generation_storage_statements.update_unknown_generation()
        generation_storage_statements.assert_not_found_error_raised()


class TestUpdateConcurrentConflict:
    """Updating with a stale version raises ConflictException instead of silently
    overwriting a concurrent update (optimistic locking)."""

    async def test_should_raise_conflict_for_stale_version(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        generation = generation_storage_statements.build_pending_generation()
        await generation_storage_statements.save_generation(generation)
        await generation_storage_statements.fetch_by_saved_id()
        stale_copy = generation_storage_statements.fetched_generation
        await generation_storage_statements.fetch_by_saved_id()
        fresh_copy = generation_storage_statements.fetched_generation

        fresh_copy.mark_in_progress()
        await generation_storage_statements.update_generation(fresh_copy)

        stale_copy.complete("Готовый доклад")
        await generation_storage_statements.update_generation_with_stale_version(stale_copy)
        generation_storage_statements.assert_conflict_error_raised()


class TestListStale:
    """list_stale finds pending/in_progress generations older than the threshold
    and excludes fresh ones, so the sweep usecase can recover crashed workers.
    It is cross-owner by design -- the sweep recovers every stuck row."""

    async def test_should_include_stale_pending_generation(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        stale = await generation_storage_statements.save_stale_pending_generation()
        await generation_storage_statements.list_stale_generations(older_than_minutes=10)
        generation_storage_statements.assert_stale_generations_include(stale)

    async def test_should_exclude_fresh_pending_generation(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.given_an_account()
        fresh = await generation_storage_statements.save_fresh_pending_generation()
        await generation_storage_statements.list_stale_generations(older_than_minutes=10)
        generation_storage_statements.assert_stale_generations_exclude(fresh)
