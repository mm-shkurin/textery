from datetime import UTC, datetime
from uuid import UUID, uuid4

# Imported for use below AND re-exported: the constants moved to
# `generation_rules` for file size, not to be renamed, so every existing
# `from generation.generation import PENDING_STATUS` must keep resolving.
from generation.generation_rules import (  # noqa: F401
    COMPLETED_STATUS,
    EXTRA_WISHES_TOO_LONG_MESSAGE,
    FAILED_STATUS,
    IN_PROGRESS_STATUS,
    INVALID_DOCUMENT_TYPE_MESSAGE,
    MAX_EXTRA_WISHES_LENGTH,
    MAX_REQUIREMENTS_LENGTH,
    MAX_TOPIC_LENGTH,
    MAX_VOLUME_PAGES,
    MIN_VOLUME_PAGES,
    MISSING_TOPIC_MESSAGE,
    OUT_OF_RANGE_VOLUME_MESSAGE,
    PENDING_STATUS,
    REQUIREMENTS_TOO_LONG_MESSAGE,
    TOPIC_TOO_LONG_MESSAGE,
)
from generation.generation_validation import (
    is_out_of_range_volume,
    required_topic,
    validate_document_type,
    validated_retry_volume,
)
from generation.text_style import validate_text_style
from shared.exceptions import ValidationException


class Generation:
    def __init__(
        self,
        id: UUID,
        owner_id: UUID,
        status: str,
        created_at: datetime,
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None,
        extra_wishes: str | None,
        document_type: str,
        content: str | None = None,
        error_message: str | None = None,
        version: int = 1,
        idempotency_key: str | None = None,
        source_generation_id: UUID | None = None,
        text_style: str | None = None,
    ) -> None:
        self.id = id
        # Required positionally, with no default: a default would let a caller that
        # forgot the owner construct an unowned generation and only fail later at the
        # NOT NULL column, far from the mistake.
        self.owner_id = owner_id
        self.status = status
        self.created_at = created_at
        self.version = version
        self.topic = topic
        self.volume_pages = volume_pages
        self.requirements = requirements
        self.extra_wishes = extra_wishes
        self.document_type = document_type
        self.content = content
        self.error_message = error_message
        # Both default to None because every generation created before retries
        # existed has neither. NULL is "no key was ever supplied", which is a
        # different statement from "the empty key" -- and the one the unique
        # index needs, since Postgres treats NULLs as distinct.
        self.idempotency_key = idempotency_key
        self.source_generation_id = source_generation_id
        # Unvalidated here, like every other field on this path: __init__ is the
        # storage hydration route, and a row written under an older allowlist must
        # read back as it was rather than raise on a value the user cannot change.
        # `style_instruction` is what degrades an unrecognised value to no
        # sentence at all when the prompt is built.
        self.text_style = text_style

    def mark_in_progress(self) -> None:
        self.status = IN_PROGRESS_STATUS

    def complete(self, content: str) -> None:
        self.content = content
        self.status = COMPLETED_STATUS

    def fail(self, reason: str) -> None:
        self.error_message = reason
        self.status = FAILED_STATUS

    def requeue(self) -> None:
        self.status = PENDING_STATUS

    @classmethod
    def create(
        cls,
        owner_id: UUID,
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None,
        extra_wishes: str | None,
        document_type: str,
        text_style: str | None = None,
    ) -> "Generation":
        # Rebinding to the non-optional return is what lets the length check below
        # be honest: a predicate that answers True for None leaves `topic` typed
        # `str | None` afterwards, and `len(topic)` was only safe by reading the
        # two lines together. The validator returns the narrowed value instead.
        topic = required_topic(topic)
        if len(topic) > MAX_TOPIC_LENGTH:
            raise ValidationException(TOPIC_TOO_LONG_MESSAGE)
        if is_out_of_range_volume(volume_pages):
            raise ValidationException(OUT_OF_RANGE_VOLUME_MESSAGE)
        if requirements is not None and len(requirements) > MAX_REQUIREMENTS_LENGTH:
            raise ValidationException(REQUIREMENTS_TOO_LONG_MESSAGE)
        if extra_wishes is not None and len(extra_wishes) > MAX_EXTRA_WISHES_LENGTH:
            raise ValidationException(EXTRA_WISHES_TOO_LONG_MESSAGE)
        return cls(
            id=uuid4(),
            owner_id=owner_id,
            status=PENDING_STATUS,
            created_at=datetime.now(UTC),
            topic=topic,
            volume_pages=volume_pages,
            requirements=requirements,
            extra_wishes=extra_wishes,
            document_type=validate_document_type(document_type),
            text_style=validate_text_style(text_style),
        )

    @classmethod
    def retry_of(
        cls,
        source: "Generation",
        idempotency_key: str,
        *,
        text_style: str | None = None,
        volume_pages: int | None = None,
    ) -> "Generation":
        """A fresh run of `source`, from the parameters stored on that row.

        Every field EXCEPT the two named overrides is copied from the source row
        rather than taken from the request, which is what keeps the retry endpoint
        bodiless in its plain form: there is no `owner_id`, `status`, `id` or
        timestamp for a client to over-bind, because none of them is read from a
        client at all.

        The new row starts `pending` with a server-assigned id and creation
        instant -- never the source's status, and never `completed` carried
        across, which would produce a finished generation that was never run.

        **Copied fields are deliberately NOT re-validated.** The source row is
        already stored, and refusing here would strand a user whose generation was
        created under an older, wider rule with a button that can never succeed. A
        document type that is no longer offered is caught downstream by the
        provider.

        **The overrides ARE validated**, and the asymmetry is the point: a copied
        value is history, which the user cannot change and must not be punished
        for, while an override is a fresh choice arriving from a client right now.
        The same value gets opposite treatment depending on where it came from,
        which is why the two are resolved by `_overridden` below rather than by
        one rule applied to the whole row.

        `None` on an override means "not overridden", never "clear it". Neither
        register nor length has a meaningful empty state a user would ask for, so
        no caller needs to say the other thing and no caller can say it by
        accident.

        Keyword-only, and not for style: `text_style` is a `str` and
        `volume_pages` an `int`, so a transposition would be caught today -- but a
        third override of either type would not be, and the barrier costs nothing
        now while adding it later costs every call site.
        """
        return cls(
            id=uuid4(),
            owner_id=source.owner_id,
            status=PENDING_STATUS,
            created_at=datetime.now(UTC),
            topic=source.topic,
            requirements=source.requirements,
            extra_wishes=source.extra_wishes,
            document_type=source.document_type,
            idempotency_key=idempotency_key,
            source_generation_id=source.id,
            # «Перегенерировать в другом стиле» and «изменить объём»: the two
            # things a user genuinely re-chooses at the moment of a retry. An
            # absent override keeps the source's own value, so the plain
            # «Повторить» button stays bodiless.
            text_style=(
                source.text_style if text_style is None else validate_text_style(text_style)
            ),
            volume_pages=(
                source.volume_pages
                if volume_pages is None
                else validated_retry_volume(volume_pages)
            ),
        )
