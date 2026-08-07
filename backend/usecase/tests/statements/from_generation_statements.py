from datetime import UTC, datetime
from uuid import UUID, uuid4

from document.create_document_from_generation import CreateDocumentFromGeneration
from fake.generation.fake_generation_storage import FakeGenerationStorage
from generation.generation import Generation

_EPOCH = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)

COMPLETED_MARKDOWN = "# Доклад\n\nПервый абзац.\n\n## Введение\n\nВторой абзац."


def a_completed_generation(
    owner_id: UUID,
    content: str | None = COMPLETED_MARKDOWN,
    topic: str | None = "Лексус LS 460",
    status: str = "completed",
) -> Generation:
    """A generation in the one state that can become a document.

    Defaults to the happy path so each test names only the field it is about --
    the status/content/topic a refusal test cares about is then the single visible
    difference between it and a conversion that would have succeeded.
    """
    return Generation(
        id=uuid4(),
        owner_id=owner_id,
        status=status,
        created_at=_EPOCH,
        topic=topic,
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="доклад",
        content=content,
    )


def a_generation_storage(*generations: Generation) -> FakeGenerationStorage:
    """The shared `FakeGenerationStorage`, pre-seeded with these rows.

    A seeding helper and not a second fake. There used to be a class of that same
    name declared right here, with its own constructor and its own subset of the
    `GenerationStorage` port -- so "the generation fake" named two different
    objects depending on the import line, and a port method added to one was
    absent from the other with nothing to say so. The one in `fake/generation/`
    mirrors the real adapter's CAS conflicts and its owner predicate; this file
    only ever needed the seeding shape, which is what the helper supplies.
    """
    storage = FakeGenerationStorage(call_order=[])
    for generation in generations:
        storage.seed(generation)
    return storage


class PassthroughMarkdownConverter:
    """Records what it was handed and returns it wrapped, without a real parser.

    The usecase's job is ORDER (convert, then sanitize, then cap), not markdown
    grammar -- that is pinned against the real parser in the rendering adapter's
    suite. A stand-in here keeps these tests about the usecase and makes the
    order observable: whatever this returns is what the sanitizer must receive.
    """

    MARKER = "<p>converted</p>"

    def __init__(self) -> None:
        self.received: list[str] = []

    def to_html(self, markdown_text: str) -> str:
        self.received.append(markdown_text)
        return f"{self.MARKER}{markdown_text}"


class RecordingSanitizer:
    """Passes content through unchanged, remembering every string it saw."""

    def __init__(self) -> None:
        self.received: list[str] = []

    def sanitize(self, content: str) -> str:
        self.received.append(content)
        return content


class OverflowingSanitizer:
    """Returns more than the content cap allows.

    Models the real hazard the cap-last ordering exists for: sanitization ESCAPES
    bare angle brackets, so its output can be longer than its input, and a
    document just under the limit can cross it during the step after conversion.
    """

    def __init__(self, length: int) -> None:
        self.length = length

    def sanitize(self, content: str) -> str:
        return "a" * self.length


class FixedClock:
    def __init__(self, now: datetime = _EPOCH) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def a_conversion(
    document_repository,
    generation_storage,
    markdown_converter=None,
    html_sanitizer=None,
) -> CreateDocumentFromGeneration:
    return CreateDocumentFromGeneration(
        document_repository=document_repository,
        generation_storage=generation_storage,
        markdown_converter=markdown_converter or PassthroughMarkdownConverter(),
        html_sanitizer=html_sanitizer or RecordingSanitizer(),
        clock=FixedClock(),
    )
