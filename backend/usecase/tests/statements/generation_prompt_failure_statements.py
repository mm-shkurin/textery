from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from document.document_type import DOKLAD, SUPPORTED_DOCUMENT_TYPES
from fake.generation.fake_generation_provider import FakeGenerationProvider
from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generate_document import GenerateDocument
from generation.generation import MAX_VOLUME_PAGES, Generation
from statements.arranged import arranged
from statements.generation_prompt_failure_assertions import GenerationPromptFailureAssertions
from statements.generation_row_fields import (
    assert_no_field_escaped_this_list,
    invariant_fields,
)

# The two ways a request must reach `PromptBuildError`, by different call paths in
# `build_prompt`: an over-ceiling volume fails in `_reject_unrenderable_fields`
# before any template is selected; an unsupported type clears both renderability
# guards and fails at the `_TEMPLATES` lookup. G5 requires both -- an
# unknown-type-only fixture leaves the ceiling path's retry behaviour unasserted.
# Note the tense: only the ceiling path raises `PromptBuildError` today, the lookup
# is a bare subscript raising `KeyError`. G17(a) makes green convert it.
UNSUPPORTED_TYPE = "диссертация"
OVER_CEILING_VOLUME_PAGES = MAX_VOLUME_PAGES + 1

# What the provider would have returned had it been reached. Non-empty on purpose: a
# run completing with this content is a run where the build never happened.
PROVIDER_CONTENT = "Готовый доклад"


def _reject_a_type_that_became_supported(document_type: str) -> None:
    """The premise the unsupported-type fixture rests on, checked rather than trusted.

    `UNSUPPORTED_TYPE` cannot be derived -- every derivation reads the tuple it must
    stay outside of -- so the literal is guarded. Without it, adding "диссертация" to
    the allowlist leaves that test green with the unsupported path exercised by
    neither fixture.

    Called from the arrange step rather than asserted at module scope, where this
    used to live: an import-time `assert` fires as a *collection* error attributed to
    this module rather than as a failure of the test whose premise it is, and via
    `conftest.py` it takes the whole usecase suite's collection down with it. `raise`
    rather than `assert` for the same reason `prompt_template.py:98` is being removed
    in this scenario -- `python -O` strips the statement, not the premise.
    """
    if document_type in SUPPORTED_DOCUMENT_TYPES:
        raise AssertionError(
            f"{document_type} was chosen because it is outside SUPPORTED_DOCUMENT_TYPES "
            f"and is now inside it -- this scenario's unsupported-type arrangement no "
            f"longer arranges anything, got {SUPPORTED_DOCUMENT_TYPES}"
        )


class GenerationPromptFailureStatements(GenerationPromptFailureAssertions):
    """A generation whose prompt cannot be built terminates without a provider call.

    Both fields below reach the entity through `Generation.__init__` -- the storage
    hydration path -- which applies neither `create`'s allowlist check nor its range
    check. Not a contrived seam: the row is read back from storage by
    `GenerateDocument`, and a deploy step or direct write puts either value there.

    The assertion half lives in `GenerationPromptFailureAssertions`, split out when
    widening the unaltered-row check pushed this file past the 200-line cap.
    """

    def __init__(self) -> None:
        # Held rather than passed anonymously: it is the only state proving the
        # *ordering* half of the claim, and a fake handed a throwaway list records
        # the sequence into something no assertion can read.
        self.call_order: list = []
        self.storage = FakeGenerationStorage(call_order=self.call_order)
        self.provider = FakeGenerationProvider()
        self.provider.content_to_return = PROVIDER_CONTENT
        self.slept_for: list[float] = []
        self._seeded_fields: tuple[Any, ...] | None = None

    @property
    def seeded_fields(self) -> tuple[Any, ...]:
        """`INVARIANT_FIELD_NAMES`' values as they were **at seed time**.

        By value, not by holding the entity, and that is the point. The fake hands
        the usecase the very instance seeded here, which it mutates in place, while
        `updated_generations` are `deepcopy` snapshots -- so comparing a snapshot
        against a live alias moved **both** sides together, and a usecase coercing
        `document_type` or `volume_pages` into something renderable passed the check
        written to catch exactly that. Only `id` was ever real. `arranged` stays for
        the sibling Statements' reason: the provider and sleep assertions both pass
        on an instance whose act step never ran.

        Nine fields rather than the three this started as: `owner_id` and `version`
        are the two that make the unaltered claim load-bearing on *this* path -- a
        `fail()` written against a rewritten owner is a lost update on somebody
        else's row, and a bumped version is a broken CAS -- and neither was compared.
        `topic`, `requirements`, `extra_wishes` and `created_at` are the user's own
        text and the sweep's clock, invariant for the same reason `document_type` is.
        """
        return arranged(self._seeded_fields, "_seeded_fields")

    async def process_a_generation_with_an_unsupported_document_type(self) -> None:
        _reject_a_type_that_became_supported(UNSUPPORTED_TYPE)
        await self._process(document_type=UNSUPPORTED_TYPE, volume_pages=3)

    async def process_a_generation_whose_volume_breaches_the_ceiling(self) -> None:
        await self._process(document_type=DOKLAD, volume_pages=OVER_CEILING_VOLUME_PAGES)

    async def _process(self, document_type: str, volume_pages: int) -> None:
        generation = Generation(
            id=uuid4(),
            owner_id=uuid4(),
            status="pending",
            created_at=datetime.now(UTC),
            topic="Как работает фотосинтез",
            volume_pages=volume_pages,
            requirements=None,
            extra_wishes=None,
            document_type=document_type,
        )
        # Checked against the entity actually seeded, so the field list is verified
        # on the same object the assertions later read -- not against a type stub
        # that could drift from it.
        assert_no_field_escaped_this_list(generation)
        self._seeded_fields = invariant_fields(generation)
        self.storage.seed(generation)
        usecase = GenerateDocument(
            storage=self.storage, provider=self.provider, sleep=self._record_sleep
        )
        await usecase.execute(generation.id, generation.owner_id)

    async def _record_sleep(self, seconds: float) -> None:
        self.slept_for.append(seconds)
