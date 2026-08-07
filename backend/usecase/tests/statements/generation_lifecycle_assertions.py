"""Assertion half of GenerationLifecycleStatements (split to stay under 200 lines).

A mixin, on the pattern `GenerationPromptFailureAssertions` already sets: every
attribute it reads is initialised by `GenerationLifecycleStatements.__init__`, and
its `storage`, `provider`, `looked_up_result` and `seeded_generation` are that
class's properties. Kept beside the arrange half so the DSL still reads as one
Statements object at the call site.
"""

from fake.generation.fake_generation_provider import FakeGenerationProvider
from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generate_document import _RETRY_BASE_DELAY_SECONDS, GENERIC_FAILURE_MESSAGE
from generation.generation import Generation


class GenerationLifecycleAssertions:
    """The attributes below are supplied by the arrange half, never by this one.

    Declared as properties rather than as bare annotations because that is what
    `GenerationLifecycleStatements` defines them as, and a bare annotation is a
    *writeable* attribute -- mypy rejects a read-only property overriding one.
    Each raises, so mixing this half into anything that does not supply them fails
    by name instead of returning `None` into the assertions below.
    """

    slept_for: list[float]

    @property
    def storage(self) -> FakeGenerationStorage:
        raise NotImplementedError

    @property
    def provider(self) -> FakeGenerationProvider:
        raise NotImplementedError

    @property
    def seeded_generation(self) -> Generation:
        raise NotImplementedError

    @property
    def looked_up_result(self) -> Generation:
        raise NotImplementedError

    # A plain writeable attribute on the arrange half, not a checked property --
    # declared the same way here, or mypy reports the narrowing as an override.
    result: Generation | None

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
