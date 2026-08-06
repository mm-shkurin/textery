from provider.fake_provider import FAKE_DOKLAD_TEXT, FakeProvider

# Any prompt at all: the claim under test is that the fake ignores it. A prompt
# built from the domain would suggest the content mattered here, and it does not.
_ANY_PROMPT = "доклад на тему: Космос (3 стр.)"


class TestFakeProviderGenerate:
    """FakeProvider returns the canned doklad text regardless of the prompt."""

    async def test_should_return_fake_doklad_text(self):
        result = await FakeProvider().generate(_ANY_PROMPT)

        assert result == FAKE_DOKLAD_TEXT
