from uuid import uuid4

import pytest

from shared.exceptions import ConflictException, NotFoundException
from statements.document_state import CONTENT_AT_THE_MAXIMUM, CONTENT_PAST_THE_MAXIMUM
from statements.save_document_statements import SaveStatements


@pytest.fixture
def statements():
    return SaveStatements()


class TestSaveHappyPath:
    """Scenario 6.1: saving persists the content and advances the version."""

    async def test_should_store_sanitized_content_and_advance_the_version(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving(document, owner_id, content="<p>привет</p>")

        statements.assert_saved(content="<p>привет</p>", version=2)
        statements.assert_sanitizer_saw(["<p>привет</p>"], "content must go through the sanitizer")
        statements.assert_committed_once()
        # A content-only save leaves the title alone. On an untitled document the
        # preserved value is None, which is also what an omitted `title=` kwarg
        # would NOT produce — the fake's sentinel carries a visible value.
        await statements.assert_stored_title(document, None)

    async def test_should_return_what_was_stored_not_what_was_submitted(self, statements):
        # Scenario 7.2: when sanitization alters the content, the response reflects
        # what actually landed. The fake strips <script>, so an echo of the request
        # would still carry it.
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving(
            document, owner_id, content="<p>ok</p><script>alert(1)</script>"
        )

        statements.assert_saved_content(
            "<p>ok</p>alert(1)",
            "the response must be built from the stored value, never echoed from the request",
        )
        await statements.assert_response_matches_storage(document)


class TestSaveValidation:
    """Scenarios 5.1 / 5.2: oversized content is rejected whole, never truncated."""

    async def test_should_reject_content_past_the_maximum_without_writing(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving_is_invalid(
            document, owner_id, content=CONTENT_PAST_THE_MAXIMUM
        )

        statements.assert_rejected_with("CONTENT_TOO_LONG")
        await statements.assert_nothing_was_written(document)
        statements.assert_no_title_intent_was_forwarded()
        statements.assert_sanitizer_saw(
            [],
            "oversized content must be rejected BEFORE sanitizing — otherwise an adversarial "
            "payload is fully parsed before we decline it",
        )

    async def test_should_accept_content_at_exactly_the_maximum(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving(document, owner_id, content=CONTENT_AT_THE_MAXIMUM)

        statements.assert_saved_content(
            CONTENT_AT_THE_MAXIMUM,
            "the boundary-sized content must land byte-for-byte, not merely at the right length",
        )
        await statements.assert_response_matches_storage(document)

    @pytest.mark.parametrize("version", [0, -1])
    async def test_should_reject_a_non_positive_version(self, statements, version):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving_is_invalid(
            document, owner_id, content="<p>x</p>", version=version
        )

        statements.assert_rejected_with("INVALID_VERSION")


class TestSaveConflictAndAbsence:
    async def test_should_report_not_found_for_an_unknown_document(self, statements):
        unknown_id = uuid4()

        await statements.when_saving_is_refused(
            NotFoundException, document_id=unknown_id, owner_id=uuid4(), content="<p>x</p>"
        )

        # The exception TYPE alone does not say which guard raised it — a lookup
        # bug anywhere in execute() also surfaces as NotFoundException. Pinning
        # the message pins the branch, and pins that the answer names only the id
        # the caller already sent (Security 7.1: it must reveal nothing else).
        statements.assert_refused_with_message(f"document {unknown_id} not found")

    async def test_should_report_not_found_for_another_owners_document(self, statements):
        # Security 7.1: 404, not 409 — even though the version is correct. Answering
        # 409 would confirm both that the id exists and that the version guess was right.
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving_is_refused(
            NotFoundException,
            document_id=document.id,
            owner_id=uuid4(),
            content="<p>hijack</p>",
        )

        statements.assert_refused_with_message(f"document {document.id} not found")
        # The refusal is only half the security claim. The half that makes this an
        # incident if it breaks is that "<p>hijack</p>" never touched the victim's
        # document — asserted over EVERY field, so a write that landed on title or
        # updated_at instead of content is caught too.
        await statements.assert_nothing_was_written(document)

    async def test_should_report_conflict_on_a_stale_version(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)
        await statements.when_saving(document, owner_id, content="<p>first</p>")

        await statements.when_saving_is_refused(
            ConflictException,
            document_id=document.id,
            owner_id=owner_id,
            content="<p>second</p>",
        )

        statements.assert_refused_with_message(f"document {document.id} was modified concurrently")
        await statements.assert_stored_content(
            document, "<p>first</p>", "the first save's content must survive"
        )

    async def test_should_treat_an_identical_resubmit_as_a_replay_not_a_conflict(self, statements):
        # Scenario 6.2. The client retried and its content already landed; answering
        # 409 would send it into a refetch loop over a save that succeeded.
        # Narrow on purpose: only when the stored content equals ours AND the version
        # advanced by exactly one. A content -> other -> content history still conflicts.
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)
        await statements.when_saving(document, owner_id, content="<p>same</p>")

        await statements.when_saving(document, owner_id, content="<p>same</p>")

        # The expected sequence is spelled out, so it pins the COUNT as well as
        # the value: two submits produced two saves, both at version 2.
        statements.assert_saves_landed_on_versions([2, 2])
        statements.assert_saved_content("<p>same</p>", "the replay must return the stored content")
        await statements.assert_response_matches_storage(document)
