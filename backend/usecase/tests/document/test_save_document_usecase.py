from uuid import uuid4

import pytest

from shared.exceptions import ConflictException, NotFoundException
from statements.save_document_statements import SaveStatements

MAX_CONTENT = 200_000


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
        await statements.assert_response_matches_storage(document, owner_id)


class TestSaveValidation:
    """Scenarios 5.1 / 5.2: oversized content is rejected whole, never truncated."""

    async def test_should_reject_content_past_the_maximum_without_writing(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving_is_invalid(document, owner_id, content="a" * (MAX_CONTENT + 1))

        statements.assert_rejected_with("CONTENT_TOO_LONG")
        await statements.assert_nothing_was_written(document, owner_id)
        statements.assert_sanitizer_saw(
            [],
            "oversized content must be rejected BEFORE sanitizing — otherwise an adversarial "
            "payload is fully parsed before we decline it",
        )

    async def test_should_accept_content_at_exactly_the_maximum(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        await statements.when_saving(document, owner_id, content="a" * MAX_CONTENT)

        statements.assert_saved_content(
            "a" * MAX_CONTENT,
            "the boundary-sized content must land byte-for-byte, not merely at the right length",
        )

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
        await statements.when_saving_is_refused(
            NotFoundException, document_id=uuid4(), owner_id=uuid4(), content="<p>x</p>"
        )

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

        await statements.assert_stored_content(
            document, owner_id, "<p>first</p>", "the first save's content must survive"
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

        statements.assert_every_save_landed_on_version(2)
        statements.assert_saved_content("<p>same</p>", "the replay must return the stored content")
