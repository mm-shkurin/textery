"""The acts and assertions of the generation lifecycle, over `GenerationArrangement`.

The arrangement half -- the seeded row, the fakes, the ids, the recorded backoff --
lives in `generation_arrangement`, split out when this file outgrew the file-size
limit. What remains is what a lifecycle test actually says: run one of the two
usecases over the arranged generation, then read the result and the rows written.
"""

from uuid import UUID

from fake.generation.fake_generation_provider import FakeGenerationProvider
from generation.generate_document import (
    _RETRY_BASE_DELAY_SECONDS,
    GENERIC_FAILURE_MESSAGE,
    GenerateDocument,
)
from generation.get_generation import GetGeneration
from statements.generation_arrangement import GenerationArrangement


class GenerationLifecycleStatements(GenerationArrangement):
    async def look_up_generation_status(self) -> None:
        usecase = GetGeneration(storage=self.storage)
        self.result = await usecase.execute(self.looked_up_id, self.looked_up_owner_id)

    def assert_status_pending_without_content(self) -> None:
        assert self.result is not None, "expected a Generation to be returned, got None"
        assert self.result.status == "pending", (
            f"expected status 'pending', got '{self.result.status}'"
        )
        assert self.result.content is None, f"expected content None, got '{self.result.content}'"

    def assert_status_completed_with_content(self, expected_content: str) -> None:
        assert self.result is not None, "expected a Generation to be returned, got None"
        assert self.result.status == "completed", (
            f"expected status 'completed', got '{self.result.status}'"
        )
        assert self.result.content == expected_content, (
            f"expected content '{expected_content}', got '{self.result.content}'"
        )

    def assert_generation_not_found(self) -> None:
        assert self.result is None, f"expected None for unknown id, got {self.result}"

    def assert_foreign_generation_withheld(self) -> None:
        """Same assertion as `assert_generation_not_found`, named separately: the
        point under test is that a foreign generation is indistinguishable from an
        absent one, so the two must produce the identical result.
        """
        assert self.result is None, (
            f"expected a foreign generation to be withheld as None, got {self.result}"
        )

    def _a_fresh_provider(self) -> FakeGenerationProvider:
        """Returned as well as stored, so a caller configures it in one line."""
        self._provider = FakeGenerationProvider()
        return self._provider

    async def _process(self, generation_id: UUID, owner_id: UUID) -> None:
        """The wiring every processing act shares, written once.

        Four acts differ only in how the provider is told to behave and which id
        they present; the usecase construction -- and in particular that `sleep` is
        the recorder rather than real time -- is the same at all of them, and an act
        added later that rebuilt it by hand could quietly wait out a real backoff.
        """
        usecase = GenerateDocument(
            storage=self.storage, provider=self.provider, sleep=self._record_sleep
        )
        await usecase.execute(generation_id, owner_id)

    async def _process_the_seeded_generation(self) -> None:
        await self._process(self.seeded_generation.id, self.seeded_generation.owner_id)

    async def process_pending_generation_with_provider_success(
        self, content: str = "Готовый доклад"
    ) -> None:
        self.given_pending_generation()
        self._a_fresh_provider().content_to_return = content
        await self._process_the_seeded_generation()

    async def process_pending_generation_with_provider_error(self, error: Exception) -> None:
        self.given_pending_generation()
        self._a_fresh_provider().error_to_raise = error
        await self._process_the_seeded_generation()

    async def process_pending_generation_with_transient_provider_error(
        self, error: Exception, fail_times: int, content: str = "Готовый доклад"
    ) -> None:
        self.given_pending_generation()
        provider = self._a_fresh_provider()
        provider.error_to_raise = error
        provider.fail_times = fail_times
        provider.content_to_return = content
        await self._process_the_seeded_generation()

    async def process_a_generation_that_is_gone(self) -> None:
        """Run GenerateDocument against an id the storage does not hold.

        Reachable without a bug: the sweep re-triggers execution from a list read
        taken earlier, so the row can be deleted between that read and this call.
        """
        self.given_no_generation()
        self._a_fresh_provider()
        await self._process(self.looked_up_id, self.looked_up_owner_id)

    def assert_no_generation_was_written(self) -> None:
        assert self.storage.updated_generations == [], (
            "expected no write for a generation that does not exist, got "
            f"{self.storage.updated_generations}"
        )

    def assert_provider_was_not_called(self) -> None:
        assert self.provider.call_count == 0, (
            "expected the provider not to be called for a generation that does not "
            f"exist, got {self.provider.call_count} calls"
        )

    def assert_waited_before_retrying(self) -> None:
        """A retry that fires instantly re-hits whatever was still broken."""
        assert len(self.slept_for) == 1, (
            f"expected exactly one backoff between two attempts, got {self.slept_for}"
        )
        assert self.slept_for[0] >= _RETRY_BASE_DELAY_SECONDS, (
            f"expected to wait at least the base delay, got {self.slept_for[0]}s"
        )

    def assert_never_waited(self) -> None:
        """No backoff after the final attempt: nothing is left to wait for."""
        assert self.slept_for == [], f"expected no backoff, got {self.slept_for}"

    def assert_provider_call_count(self, expected_count: int) -> None:
        assert self.provider.call_count == expected_count, (
            f"expected provider called {expected_count} times, got {self.provider.call_count}"
        )

    def assert_generation_completed_with_content(self, expected_content: str) -> None:
        stored = self.storage.updated_generations[-1]
        assert stored.status == "completed", f"expected status 'completed', got '{stored.status}'"
        assert stored.content == expected_content, (
            f"expected content '{expected_content}', got '{stored.content}'"
        )

    def assert_generation_failed_with_reason(self, expected_reason: str) -> None:
        stored = self.storage.updated_generations[-1]
        assert stored.status == "failed", f"expected status 'failed', got '{stored.status}'"
        assert stored.error_message == expected_reason, (
            f"expected failure reason '{expected_reason}', got '{stored.error_message}'"
        )

    def assert_generation_failed_with_generic_reason(self) -> None:
        self.assert_generation_failed_with_reason(GENERIC_FAILURE_MESSAGE)

    def assert_generation_marked_in_progress_before_final_update(self) -> None:
        statuses = [g.status for g in self.storage.updated_generations]
        assert statuses[0] == "in_progress", (
            f"expected first update() to record status 'in_progress', got {statuses}"
        )
