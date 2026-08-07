from uuid import uuid4

import pytest

from document.document_content import MAX_CONTENT_LENGTH
from document.generated_title import UNTITLED_FALLBACK
from shared.exceptions import ValidationException
from statements.document_fakes import FakeDocumentRepository
from statements.from_generation_statements import (
    COMPLETED_MARKDOWN,
    OverflowingSanitizer,
    PassthroughMarkdownConverter,
    RecordingSanitizer,
    a_completed_generation,
    a_conversion,
    a_generation_storage,
)


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def documents():
    return FakeDocumentRepository()


class TestACompletedGenerationBecomesAnEditableDocument:
    async def test_should_create_a_draft_linked_to_the_generation(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, a_generation_storage(generation))

        result = await conversion.execute(owner_id, generation.id, "key-1")

        assert result.is_replay is False
        assert result.document.generation_id == generation.id
        assert result.document.owner_id == owner_id
        assert result.document.status == "draft"
        # Version 1, not 2: the conversion is the document's FIRST state. Starting
        # higher would make the editor's first save arrive with a stale token and
        # collect a 409 blaming a concurrent save that never happened.
        assert result.document.version == 1

    async def test_should_take_the_document_type_from_the_generation(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, a_generation_storage(generation))

        result = await conversion.execute(owner_id, generation.id, "key-1")

        assert result.document.document_type == generation.document_type

    async def test_should_title_the_document_from_the_topic(self, documents, owner_id):
        generation = a_completed_generation(owner_id, topic="Лексус LS 460")
        conversion = a_conversion(documents, a_generation_storage(generation))

        result = await conversion.execute(owner_id, generation.id, "key-1")

        assert result.document.title == "Лексус LS 460"

    async def test_should_fall_back_to_an_untitled_name_without_a_topic(self, documents, owner_id):
        generation = a_completed_generation(owner_id, topic=None)
        conversion = a_conversion(documents, a_generation_storage(generation))

        result = await conversion.execute(owner_id, generation.id, "key-1")

        assert result.document.title == UNTITLED_FALLBACK

    async def test_should_persist_the_document(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, a_generation_storage(generation))

        await conversion.execute(owner_id, generation.id, "key-1")

        assert len(documents.documents) == 1

    async def test_should_leave_the_generation_untouched(self, documents, owner_id):
        # The generation stays the audit record of what the model produced, so a
        # later question about who wrote a paragraph is still answerable.
        generation = a_completed_generation(owner_id)
        generations = a_generation_storage(generation)
        conversion = a_conversion(documents, generations)

        await conversion.execute(owner_id, generation.id, "key-1")

        assert generations.updated_generations == [], (
            "the conversion must not write to the generation"
        )
        assert generation.content == COMPLETED_MARKDOWN


class TestTheContentPipelineRunsInOrder:
    """Convert, THEN sanitize, THEN cap. Each step depends on the one before."""

    async def test_should_hand_the_generated_markdown_to_the_converter(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        converter = PassthroughMarkdownConverter()
        conversion = a_conversion(documents, a_generation_storage(generation), converter)

        await conversion.execute(owner_id, generation.id, "key-1")

        assert converter.received == [COMPLETED_MARKDOWN]

    async def test_should_sanitize_the_converters_output_not_the_raw_markdown(
        self, documents, owner_id
    ):
        # The security-critical half of the ordering: markdown permits raw
        # embedded HTML, so the parser's output is the thing that must meet the
        # allowlist. Sanitizing the markdown first and converting after would let
        # a payload through in the gap.
        generation = a_completed_generation(owner_id)
        converter = PassthroughMarkdownConverter()
        sanitizer = RecordingSanitizer()
        conversion = a_conversion(documents, a_generation_storage(generation), converter, sanitizer)

        await conversion.execute(owner_id, generation.id, "key-1")

        assert sanitizer.received == [f"{PassthroughMarkdownConverter.MARKER}{COMPLETED_MARKDOWN}"]

    async def test_should_store_what_the_sanitizer_returned(self, documents, owner_id):
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(documents, a_generation_storage(generation))

        result = await conversion.execute(owner_id, generation.id, "key-1")

        assert result.document.content.startswith(PassthroughMarkdownConverter.MARKER)

    async def test_should_refuse_content_that_grows_past_the_cap_during_sanitization(
        self, documents, owner_id
    ):
        # Why the cap is measured LAST: sanitization escapes bare angle brackets,
        # so it can push a document that was under the limit over it. Capping the
        # markdown instead would fail at the database column rather than here.
        generation = a_completed_generation(owner_id)
        conversion = a_conversion(
            documents,
            a_generation_storage(generation),
            html_sanitizer=OverflowingSanitizer(MAX_CONTENT_LENGTH + 1),
        )

        with pytest.raises(ValidationException) as refusal:
            await conversion.execute(owner_id, generation.id, "key-1")

        assert refusal.value.error_code == "CONVERTED_CONTENT_TOO_LONG"
        assert documents.documents == [], "nothing may be stored when the content is refused"
