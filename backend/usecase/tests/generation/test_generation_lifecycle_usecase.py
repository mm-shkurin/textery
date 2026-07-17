
from adapters.generation_provider import ProviderError
from statements.generation_lifecycle_statements import GenerationLifecycleStatements


class TestGetGenerationStatus:
    """Scenario 4.1: A pending generation reports its status without document content."""

    async def test_should_report_pending_status_without_content(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        generation_lifecycle_statements.given_pending_generation()
        await generation_lifecycle_statements.look_up_generation_status()
        generation_lifecycle_statements.assert_status_pending_without_content()


class TestGetGenerationCompleted:
    """Scenario 4.2: A completed generation includes the document content."""

    async def test_should_report_completed_status_with_content(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        generation_lifecycle_statements.given_completed_generation(content="Готовый доклад")
        await generation_lifecycle_statements.look_up_generation_status()
        generation_lifecycle_statements.assert_status_completed_with_content("Готовый доклад")


class TestGetGenerationNotFound:
    """Scenario 4.3: Requesting a non-existent generation reports not found."""

    async def test_should_return_none_for_unknown_id(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        generation_lifecycle_statements.given_no_generation()
        await generation_lifecycle_statements.look_up_generation_status()
        generation_lifecycle_statements.assert_generation_not_found()


class TestGenerateDocumentSuccess:
    """Evening-demo slice: a successful provider call completes the generation."""

    async def test_should_complete_generation_with_provider_content(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        await generation_lifecycle_statements.process_pending_generation_with_provider_success(
            content="Готовый доклад"
        )
        generation_lifecycle_statements.assert_generation_completed_with_content("Готовый доклад")
        generation_lifecycle_statements.assert_generation_marked_in_progress_before_final_update()


class TestGenerateDocumentProviderFailure:
    """Evening-demo slice: a provider error fails the generation with a generic, sanitized reason."""

    async def test_should_fail_generation_with_generic_reason(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        await generation_lifecycle_statements.process_pending_generation_with_provider_error(
            ProviderError("https://gigachat.devices.sberbank.ru/api/v1/chat/completions: connection refused")
        )
        generation_lifecycle_statements.assert_generation_failed_with_generic_reason()
        generation_lifecycle_statements.assert_generation_marked_in_progress_before_final_update()

    async def test_should_retry_provider_once_before_giving_up(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        await generation_lifecycle_statements.process_pending_generation_with_provider_error(
            ProviderError("provider unavailable")
        )
        generation_lifecycle_statements.assert_provider_call_count(2)


class TestGenerateDocumentTransientProviderFailure:
    """Evening-demo slice: a transient provider error is retried and can still succeed."""

    async def test_should_complete_generation_after_one_transient_failure(
        self, generation_lifecycle_statements: GenerationLifecycleStatements
    ):
        await generation_lifecycle_statements.process_pending_generation_with_transient_provider_error(
            ProviderError("temporary blip"), fail_times=1, content="Готовый доклад"
        )
        generation_lifecycle_statements.assert_generation_completed_with_content("Готовый доклад")
        generation_lifecycle_statements.assert_provider_call_count(2)
