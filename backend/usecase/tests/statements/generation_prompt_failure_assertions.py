from typing import Any

from fake.generation.fake_generation_provider import FakeGenerationProvider
from fake.generation.fake_generation_storage import (
    CALL_GET,
    CALL_UPDATE,
    FakeGenerationStorage,
)
from statements.generation_row_fields import INVARIANT_FIELD_NAMES, invariant_fields

# The sanctioned failure text, **retyped rather than imported** from
# `generate_document`, on `test_prompt_build_refusals.py`'s reasoning: importing it
# makes the assertion `str == the string the code just wrote`, true of any message --
# including one that grew a slot quoting the offending `document_type`, the very leak
# it claims to prevent. Do not de-duplicate.
GENERIC_FAILURE_MESSAGE = "Не удалось сгенерировать документ. Попробуйте позже."

# What the storage must see, in order: the worker's one owner-filtered read, the
# `in_progress` mark, the terminal `failed` write. A sequence rather than three
# presence checks because the claim is an ordering one -- and because a `save`
# anywhere in here is a usecase that wrote a new row on a failure path.
EXPECTED_STORAGE_CALLS = [CALL_GET, CALL_UPDATE, CALL_UPDATE]


class GenerationPromptFailureAssertions:
    """Assertion half of GenerationPromptFailureStatements (split to stay under 200 lines).

    A mixin, on `ResendCodeAssertions`' pattern: every attribute it reads is
    initialised by `GenerationPromptFailureStatements.__init__`, and `seeded_fields`
    is that class's property. Kept beside the arrange half so the DSL still reads as
    one Statements object.
    """

    storage: FakeGenerationStorage
    provider: FakeGenerationProvider
    call_order: list
    slept_for: list[float]

    @property
    def seeded_fields(self) -> tuple[Any, ...]: ...

    def assert_provider_was_never_called(self) -> None:
        """Zero, not "fewer than two".

        Composing the prompt at the call site is what keeps a request that cannot be
        phrased from becoming a billed completion. A count of one is the signature of
        the build drifting into the provider -- the placement `progress-backend.md`
        puts Backend 2.1 under an obligation about.
        """
        assert self.provider.call_count == 0, (
            f"a prompt that cannot be built must reach no provider, got "
            f"{self.provider.call_count} call(s)"
        )

    def assert_never_waited(self) -> None:
        """A backoff before retrying a value that cannot change on attempt 2.

        Separate from the call count: a build inside the retry loop is caught by the
        count, but a catch-all that slept once and gave up still shows one call and
        has still spent the user's seconds on a deterministic failure.
        """
        assert self.slept_for == [], (
            f"a deterministic build failure must not be retried on a backoff, "
            f"waited {self.slept_for}"
        )

    def assert_storage_saw_only_the_read_and_the_two_writes(self) -> None:
        """The call sequence, not three presence checks over it.

        `save` anywhere in here is a failure path that wrote a *new* row, and a read
        after the terminal write is a second activation. Neither is visible to a
        per-collaborator count; both are visible here.
        """
        tags = [tag for tag, _ in self.call_order]

        assert tags == EXPECTED_STORAGE_CALLS, (
            f"expected the storage calls {EXPECTED_STORAGE_CALLS}, got {tags}"
        )

    def assert_failed_with_the_generic_message_after_exactly_two_updates(self) -> None:
        """Exactly two writes, and every field this scenario constrains on both.

        The count is the assertion, not decoration. Before `mark_in_progress()` the
        row stays `pending` and the stale sweep cycles it forever; a third write
        means the failure travelled through the retry loop to get terminal.

        One comparison over *both* snapshots rather than the status of each plus the
        fields of the last: a `mark_in_progress` that had already stamped an
        `error_message`, or a partial `content`, is invisible to a last-snapshot
        check and lands in the DB either way.

        `==` on the retyped constant above is also what keeps the offending
        `document_type` out of anything the client reads.
        """
        written = [(g.status, g.error_message, g.content) for g in self.storage.updated_generations]

        assert written == [
            ("in_progress", None, None),
            ("failed", GENERIC_FAILURE_MESSAGE, None),
        ], f"expected the row marked in_progress then failed once, got {written}"

    def assert_the_offending_row_was_written_back_unaltered(self) -> None:
        """**Every** write lands on the seeded row, with all nine invariants intact.

        Claims the status/message assertions do not reach. `id` and `owner_id`: a
        `fail()` written against a row this usecase never read is a lost update on
        somebody else's generation. `version`: a bump here is a broken CAS on a path
        that never earned one. `document_type` / `volume_pages`: the values that
        caused the refusal must survive it -- a usecase that coerced either into
        something renderable would satisfy every assertion above while destroying
        the only evidence of why the row failed, which 3.3 is written against.
        `topic` / `requirements` / `extra_wishes` / `created_at`: the user's own text
        and the sweep's clock, invariant for the same reason.

        Over **both** snapshots, not the last one. `EXPECTED_STORAGE_CALLS` pins two
        updates, and the sibling assertion's own docstring argues that a
        last-snapshot check is blind to a `mark_in_progress` that already corrupted
        the row -- this method was making exactly that mistake, so a first write that
        coerced `document_type` into something renderable and a second that put it
        back was green.

        Compared against `seeded_fields` -- primitives captured at seed time, not the
        seeded entity; see that property for why.
        """
        expected = self.seeded_fields
        # Explicit rather than an `IndexError` off `[-1]`: a skipped act reports as
        # the arrangement failure it is, the way `arranged` does.
        assert self.storage.updated_generations, (
            "no generation was ever written -- call the act step before this assertion"
        )
        actual = [invariant_fields(g) for g in self.storage.updated_generations]

        assert actual == [expected] * len(actual), (
            f"every write must carry the seeded row's fields "
            f"{INVARIANT_FIELD_NAMES} unaltered: seeded {expected}, wrote {actual}"
        )

    def assert_the_build_failure_was_terminal_and_unbilled(self) -> None:
        """G5 in one call: no provider, no backoff, one read, two writes, row intact.

        The five claims were spelled out as five calls in both test bodies, in the
        same order -- so a sixth claim added later had two edit sites and would
        silently have covered one path. They are one compound statement because G5
        is one: "a prompt that cannot be built costs the user nothing and ends the
        row". Ordered cheapest-signal-first, so the failure a reader sees names the
        provider call rather than a row-field diff downstream of it.
        """
        self.assert_provider_was_never_called()
        self.assert_never_waited()
        self.assert_storage_saw_only_the_read_and_the_two_writes()
        self.assert_failed_with_the_generic_message_after_exactly_two_updates()
        self.assert_the_offending_row_was_written_back_unaltered()
