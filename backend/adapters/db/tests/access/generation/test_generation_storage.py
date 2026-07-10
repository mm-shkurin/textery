from statements.generation_storage_statements import GenerationStorageStatements


class TestSaveAndGet:
    """A saved generation can be fetched back by id with all fields intact."""

    async def test_should_round_trip_saved_generation(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        generation = generation_storage_statements.build_pending_generation()
        await generation_storage_statements.save_generation(generation)
        await generation_storage_statements.fetch_by_saved_id()
        generation_storage_statements.assert_fetched_matches_saved()


class TestGetUnknownId:
    """Fetching an id that was never saved returns None."""

    async def test_should_return_none_for_unknown_id(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        await generation_storage_statements.fetch_unknown_generation()
        generation_storage_statements.assert_fetched_is_none()


class TestUpdate:
    """Updating a saved generation persists its new status and content."""

    async def test_should_persist_status_and_content_after_update(
        self, generation_storage_statements: GenerationStorageStatements
    ):
        generation = generation_storage_statements.build_pending_generation()
        await generation_storage_statements.save_generation(generation)
        generation.complete("Готовый доклад")
        await generation_storage_statements.update_generation(generation)
        await generation_storage_statements.fetch_by_saved_id()
        generation_storage_statements.assert_fetched_status_and_content("completed", "Готовый доклад")
