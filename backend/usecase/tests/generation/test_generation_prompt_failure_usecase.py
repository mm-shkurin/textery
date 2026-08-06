import pytest

from statements.generation_prompt_failure_statements import GenerationPromptFailureStatements


@pytest.mark.skip(
    reason="RED: GenerateDocument builds no prompt -- the provider is called once and the "
    "row completes; AssertionError: a prompt that cannot be built must reach no provider, "
    "got 1 call(s)"
)
class TestAPromptThatCannotBeBuiltIsNotRetried:
    """G5. A `PromptBuildError` is deterministic: attempt 2 sends the identical request.

    `generate_document.py` catches bare `Exception` and retries with a 1.0-1.5s
    backoff, so today a build failure would burn the whole retry budget, land the
    user on "попробуйте позже" -- advice that is false forever -- and log it at the
    severity routine provider blips share. This scenario is the commit that removes
    the loud module-scope guard, so it is the commit that has to carry the quiet
    one: 1.4 carries both halves or neither.

    Two cases rather than one, because the two errors arrive by different call
    paths inside `build_prompt` and only the count of provider calls is common to
    them. A fixture that only ever raises the unknown-type error leaves the ceiling
    path's retry behaviour unasserted.
    """

    async def test_should_not_call_the_provider_for_an_unsupported_document_type(
        self, generation_prompt_failure_statements: GenerationPromptFailureStatements
    ):
        statements = generation_prompt_failure_statements
        await statements.process_a_generation_with_an_unsupported_document_type()

        statements.assert_the_build_failure_was_terminal_and_unbilled()

    async def test_should_not_call_the_provider_when_the_volume_breaches_the_ceiling(
        self, generation_prompt_failure_statements: GenerationPromptFailureStatements
    ):
        statements = generation_prompt_failure_statements
        await statements.process_a_generation_whose_volume_breaches_the_ceiling()

        statements.assert_the_build_failure_was_terminal_and_unbilled()
