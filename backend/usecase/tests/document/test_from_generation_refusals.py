from uuid import uuid4

import pytest

from shared.exceptions import NotFoundException, ValidationException
from statements.document_fakes import FakeDocumentRepository
from statements.from_generation_statements import (
    FakeGenerationStorage,
    a_completed_generation,
    a_conversion,
)


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def documents():
    return FakeDocumentRepository()


class TestOnlyAFinishedGenerationTheCallerOwnsCanConvert:
    async def test_should_refuse_a_generation_that_does_not_exist(self, documents, owner_id):
        conversion = a_conversion(documents, FakeGenerationStorage([]))

        with pytest.raises(NotFoundException):
            await conversion.execute(owner_id, uuid4(), "key-1")

    async def test_should_refuse_another_accounts_generation_as_if_absent(
        self, documents, owner_id
    ):
        # Byte-identical to the missing case, never a 403: a distinguishable
        # answer confirms the id exists to whoever guessed it.
        someone_else = a_completed_generation(uuid4())
        conversion = a_conversion(documents, FakeGenerationStorage([someone_else]))

        with pytest.raises(NotFoundException):
            await conversion.execute(owner_id, someone_else.id, "key-1")

    @pytest.mark.parametrize("status", ["pending", "in_progress", "failed", "some_future_status"])
    async def test_should_refuse_any_status_that_is_not_completed(
        self, documents, owner_id, status
    ):
        # An allowlist, not a denylist: the status nobody remembers to handle is
        # the one a later story adds, and converting a half-written generation
        # would hand the user a truncated document as if it were finished.
        generation = a_completed_generation(owner_id, status=status)
        conversion = a_conversion(documents, FakeGenerationStorage([generation]))

        with pytest.raises(ValidationException) as refusal:
            await conversion.execute(owner_id, generation.id, "key-1")

        assert refusal.value.error_code == "GENERATION_NOT_COMPLETED"
        assert documents.documents == []

    async def test_should_refuse_a_completed_generation_with_no_text(self, documents, owner_id):
        # Fails closed. A completed generation carrying nothing is not something
        # to convert into an empty document the user would read as "it deleted my
        # report".
        generation = a_completed_generation(owner_id, content=None)
        conversion = a_conversion(documents, FakeGenerationStorage([generation]))

        with pytest.raises(ValidationException) as refusal:
            await conversion.execute(owner_id, generation.id, "key-1")

        assert refusal.value.error_code == "GENERATION_NOT_COMPLETED"

    async def test_should_refuse_an_empty_idempotency_key(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, FakeGenerationStorage([generation]))

        with pytest.raises(ValidationException) as refusal:
            await conversion.execute(owner_id, generation.id, "")

        assert refusal.value.error_code == "INVALID_IDEMPOTENCY_KEY"


class TestConvertingTwiceYieldsOneDocument:
    """The constraint decides, and this usecase reports who won.

    Not a nicety: React StrictMode double-invokes the effect that fires this
    request, so the second call is the NORMAL case in development, and two
    browser tabs make it the normal case in production.
    """

    async def test_should_return_the_same_document_on_a_replay(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, FakeGenerationStorage([generation]))

        first = await conversion.execute(owner_id, generation.id, "key-1")
        second = await conversion.execute(owner_id, generation.id, "key-1")

        assert second.is_replay is True
        assert second.document.id == first.document.id

    async def test_should_not_write_a_second_document_on_a_replay(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, FakeGenerationStorage([generation]))

        await conversion.execute(owner_id, generation.id, "key-1")
        await conversion.execute(owner_id, generation.id, "key-1")

        assert len(documents.documents) == 1

    async def test_should_collapse_a_lost_race_onto_the_winning_document(self, documents, owner_id):
        # A DIFFERENT key, i.e. a genuinely separate request rather than a replay
        # — a second tab, or a retry after a dropped response. The generation
        # constraint is what makes these converge; the idempotency key alone
        # would let each mint its own document.
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, FakeGenerationStorage([generation]))

        winner = await conversion.execute(owner_id, generation.id, "key-1")
        loser = await conversion.execute(owner_id, generation.id, "key-2")

        assert loser.is_replay is True
        assert loser.document.id == winner.document.id
        assert len(documents.documents) == 1

    async def test_should_refuse_a_key_that_belongs_to_an_unrelated_document(
        self, documents, owner_id
    ):
        # The key collided but no document exists for THIS generation, so the
        # caller is not replaying — returning the other document would hand them
        # somebody else's text under their own generation's name.
        first = a_completed_generation(owner_id)
        second = a_completed_generation(owner_id)
        conversion = a_conversion(documents, FakeGenerationStorage([first, second]))
        await conversion.execute(owner_id, first.id, "shared-key")

        with pytest.raises(ValidationException) as refusal:
            await conversion.execute(owner_id, second.id, "shared-key")

        assert refusal.value.error_code == "IDEMPOTENCY_KEY_REUSED"
        assert len(documents.documents) == 1
