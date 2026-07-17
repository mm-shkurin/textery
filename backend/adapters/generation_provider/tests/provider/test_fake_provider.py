from uuid import uuid4

from generation.generation import Generation
from provider.fake_provider import FAKE_DOKLAD_TEXT, FakeProvider


def _build_generation():
    return Generation.create(
        owner_id=uuid4(),
        topic="Космос",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="Доклад",
    )


class TestFakeProviderGenerate:
    """FakeProvider returns the canned doklad text regardless of the requested generation."""

    async def test_should_return_fake_doklad_text(self):
        result = await FakeProvider().generate(_build_generation())

        assert result == FAKE_DOKLAD_TEXT
