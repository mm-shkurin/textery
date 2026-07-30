from datetime import UTC, datetime
from uuid import UUID, uuid4

from document.create_document_from_generation import CreateDocumentFromGeneration
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


class FakeGenerationStorage:
    """In-memory GenerationStorage, owner-scoped like the real adapter.

    `get_by_id_and_owner` filters on owner exactly as the SQL does: a fake that
    looked up by id alone would let a conversion that forgot the ownership check
    pass here and leak another account's text in production.
    """

    def __init__(self, generations: list[Generation] | None = None) -> None:
        self.generations = generations or []
        self.updated: list[Generation] = []

    async def get_by_id_and_owner(
        self, generation_id: UUID, owner_id: UUID
    ) -> Generation | None:
        return next(
            (
                g
                for g in self.generations
                if g.id == generation_id and g.owner_id == owner_id
            ),
            None,
        )

    async def save(self, generation: Generation) -> None:
        self.generations.append(generation)

    async def update(self, generation: Generation) -> None:
        # Recorded rather than ignored: the conversion must leave the generation
        # untouched (it stays the audit record of what the model wrote), and a
        # no-op fake could not tell "never called" from "called harmlessly".
        self.updated.append(generation)

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        return []

    async def list_by_owner(self, owner_id: UUID, limit: int, cursor=None) -> list[Generation]:
        return [g for g in self.generations if g.owner_id == owner_id][:limit]


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
