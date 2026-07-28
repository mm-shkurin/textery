from uuid import uuid4

import pytest

from shared.exceptions import ConflictException, NotFoundException, ValidationException
from statements.save_document_statements import SaveStatements


@pytest.fixture
def statements():
    return SaveStatements()


class TestSaveHappyPath:
    """Scenario 6.1: saving persists the content and advances the version."""

    async def test_should_store_sanitized_content_and_advance_the_version(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        saved = await statements.usecase.execute(
            document_id=document.id, owner_id=owner_id, content="<p>привет</p>", version=1
        )

        assert saved.content == "<p>привет</p>"
        assert saved.version == 2, "a successful save advances the version by one"
        assert statements.sanitizer.sanitized == ["<p>привет</p>"], (
            "content must go through the sanitizer"
        )
        assert statements.unit_of_work.commit_call_count == 1

    async def test_should_return_what_was_stored_not_what_was_submitted(self, statements):
        # Scenario 7.2: when sanitization alters the content, the response reflects
        # what actually landed. The fake strips <script>, so an echo of the request
        # would still carry it.
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        saved = await statements.usecase.execute(
            document_id=document.id,
            owner_id=owner_id,
            content="<p>ok</p><script>alert(1)</script>",
            version=1,
        )

        assert saved.content == "<p>ok</p>alert(1)", (
            "the response must be built from the stored value, never echoed from the request"
        )
        stored = await statements.repository.find_by_id_and_owner(document.id, owner_id)
        assert stored.content == saved.content, "response and storage must not disagree"


class TestSaveValidation:
    """Scenarios 5.1 / 5.2: oversized content is rejected whole, never truncated."""

    async def test_should_reject_content_past_the_maximum_without_writing(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        with pytest.raises(ValidationException) as excinfo:
            await statements.usecase.execute(
                document_id=document.id, owner_id=owner_id, content="a" * 200_001, version=1
            )

        assert excinfo.value.error_code == "CONTENT_TOO_LONG"
        stored = await statements.repository.find_by_id_and_owner(document.id, owner_id)
        assert stored.content == "", "an oversized save must not reach storage"
        assert stored.version == 1, "a rejected save must not advance the version"
        assert statements.sanitizer.sanitized == [], (
            "oversized content must be rejected BEFORE sanitizing — otherwise an adversarial "
            "payload is fully parsed before we decline it"
        )

    async def test_should_accept_content_at_exactly_the_maximum(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        saved = await statements.usecase.execute(
            document_id=document.id, owner_id=owner_id, content="a" * 200_000, version=1
        )

        assert saved.content == "a" * 200_000, (
            "the boundary-sized content must land byte-for-byte, not merely at the right length"
        )

    @pytest.mark.parametrize("version", [0, -1])
    async def test_should_reject_a_non_positive_version(self, statements, version):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        with pytest.raises(ValidationException) as excinfo:
            await statements.usecase.execute(
                document_id=document.id, owner_id=owner_id, content="<p>x</p>", version=version
            )

        assert excinfo.value.error_code == "INVALID_VERSION"


class TestSaveConflictAndAbsence:
    async def test_should_report_not_found_for_an_unknown_document(self, statements):
        with pytest.raises(NotFoundException):
            await statements.usecase.execute(
                document_id=uuid4(), owner_id=uuid4(), content="<p>x</p>", version=1
            )

    async def test_should_report_not_found_for_another_owners_document(self, statements):
        # Security 7.1: 404, not 409 — even though the version is correct. Answering
        # 409 would confirm both that the id exists and that the version guess was right.
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)

        with pytest.raises(NotFoundException):
            await statements.usecase.execute(
                document_id=document.id, owner_id=uuid4(), content="<p>hijack</p>", version=1
            )

    async def test_should_report_conflict_on_a_stale_version(self, statements):
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)
        await statements.usecase.execute(
            document_id=document.id, owner_id=owner_id, content="<p>first</p>", version=1
        )

        with pytest.raises(ConflictException):
            await statements.usecase.execute(
                document_id=document.id, owner_id=owner_id, content="<p>second</p>", version=1
            )

        stored = await statements.repository.find_by_id_and_owner(document.id, owner_id)
        assert stored.content == "<p>first</p>", "the first save's content must survive"

    async def test_should_treat_an_identical_resubmit_as_a_replay_not_a_conflict(self, statements):
        # Scenario 6.2. The client retried and its content already landed; answering
        # 409 would send it into a refetch loop over a save that succeeded.
        # Narrow on purpose: only when the stored content equals ours AND the version
        # advanced by exactly one. A content -> other -> content history still conflicts.
        owner_id = uuid4()
        document = await statements.given_a_document(owner_id)
        first = await statements.usecase.execute(
            document_id=document.id, owner_id=owner_id, content="<p>same</p>", version=1
        )

        replay = await statements.usecase.execute(
            document_id=document.id, owner_id=owner_id, content="<p>same</p>", version=1
        )

        assert replay.version == first.version == 2, "no second version advance for a replay"
        assert replay.content == "<p>same</p>"
