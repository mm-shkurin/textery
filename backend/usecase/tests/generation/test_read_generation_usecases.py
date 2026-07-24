"""The generation read side: GetGeneration and ListGenerations.

Same gap the document read side had — both were only ever driven through the
router, where the usecase is a stub, so the owner predicate and the keyset probe
had no test running the real code.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generation import PENDING_STATUS, Generation
from generation.get_generation import GetGeneration
from generation.list_generations import ListGenerations
from shared.exceptions import ValidationException
from shared.keyset_cursor import KeysetCursor

_EPOCH = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def stored_generation(owner_id: UUID, minutes_old: int = 0) -> Generation:
    return Generation(
        id=uuid4(),
        owner_id=owner_id,
        status=PENDING_STATUS,
        created_at=_EPOCH - timedelta(minutes=minutes_old),
        topic="Тема",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="эссе",
    )


def seeded(*generations: Generation) -> FakeGenerationStorage:
    storage = FakeGenerationStorage(call_order=[])
    for generation in generations:
        storage.seed(generation)
    return storage


class TestGetGeneration:
    async def test_should_return_the_callers_own_generation(self):
        owner_id = uuid4()
        generation = stored_generation(owner_id)

        found = await GetGeneration(seeded(generation)).execute(
            generation_id=generation.id, owner_id=owner_id
        )

        assert found is generation

    async def test_should_answer_none_for_another_owners_generation(self):
        generation = stored_generation(uuid4())

        found = await GetGeneration(seeded(generation)).execute(
            generation_id=generation.id, owner_id=uuid4()
        )

        # Same answer as the unknown-id case: a distinct one would make the
        # endpoint an existence oracle over the id space.
        assert found is None

    async def test_should_answer_none_for_an_unknown_generation(self):
        found = await GetGeneration(seeded()).execute(generation_id=uuid4(), owner_id=uuid4())

        assert found is None


class TestListGenerationsOwnerScoping:
    async def test_should_return_only_the_callers_generations_newest_first(self):
        owner_id = uuid4()
        newest = stored_generation(owner_id, minutes_old=0)
        oldest = stored_generation(owner_id, minutes_old=10)
        foreign = stored_generation(uuid4(), minutes_old=5)

        page = await ListGenerations(seeded(oldest, foreign, newest)).execute(owner_id=owner_id)

        assert page.items == [newest, oldest], "another owner's generation never appears"
        assert page.next_cursor is None


class TestListGenerationsPaging:
    async def test_should_trim_the_probe_row_and_emit_a_cursor_when_more_remain(self):
        owner_id = uuid4()
        newest = stored_generation(owner_id, minutes_old=0)
        middle = stored_generation(owner_id, minutes_old=1)
        oldest = stored_generation(owner_id, minutes_old=2)

        page = await ListGenerations(seeded(newest, middle, oldest)).execute(
            owner_id=owner_id, limit=2
        )

        assert page.items == [newest, middle], "limit rows exactly — the probe row is trimmed"
        assert KeysetCursor.decode(page.next_cursor).id == middle.id, (
            "the anchor is the last row served, not the probe row"
        )

    async def test_should_resume_strictly_after_the_cursor(self):
        owner_id = uuid4()
        newest = stored_generation(owner_id, minutes_old=0)
        middle = stored_generation(owner_id, minutes_old=1)
        oldest = stored_generation(owner_id, minutes_old=2)
        usecase = ListGenerations(seeded(newest, middle, oldest))

        first = await usecase.execute(owner_id=owner_id, limit=2)
        second = await usecase.execute(owner_id=owner_id, limit=2, cursor=first.next_cursor)

        assert second.items == [oldest]
        assert second.next_cursor is None

    async def test_should_reject_a_limit_below_the_bound(self):
        with pytest.raises(ValidationException) as excinfo:
            await ListGenerations(seeded()).execute(owner_id=uuid4(), limit=0)

        assert excinfo.value.error_code == "INVALID_LIMIT"

    async def test_should_reject_an_undecodable_cursor(self):
        with pytest.raises(ValidationException) as excinfo:
            await ListGenerations(seeded()).execute(owner_id=uuid4(), cursor="not-a-cursor")

        assert excinfo.value.error_code == "INVALID_CURSOR"
