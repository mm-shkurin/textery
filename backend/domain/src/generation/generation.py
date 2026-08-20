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


def _overridden_style(source: "Generation", text_style: str | None) -> str | None:
    """The retry's register: the source's own unless the client re-chose one."""
    return source.text_style if text_style is None else validate_text_style(text_style)


def _overridden_volume(source: "Generation", volume_pages: int | None) -> int | None:
    """The retry's length: the source's own unless the client re-chose one."""
    return source.volume_pages if volume_pages is None else validated_retry_volume(volume_pages)


class Generation:
    """A generation request and the state of the run it stands for.

    Three construction paths, and the rules each applies -- hydration validating
    nothing, `create` validating every field, `retry_of` copying history
    unvalidated while validating the two overrides -- are set out in the
    `generation_rules` module docstring, alongside the bounds they enforce.
    """

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
        self._assign_identity(id, owner_id, status, created_at, version)
        self._assign_request(topic, volume_pages, requirements, extra_wishes, document_type)
        self._assign_outcome(content, error_message)
        self._assign_retry_link(idempotency_key, source_generation_id, text_style)

    def _assign_identity(
        self, id: UUID, owner_id: UUID, status: str, created_at: datetime, version: int
    ) -> None:
        self.id = id
        self.owner_id = owner_id
        self.status = status
        self.created_at = created_at
        self.version = version

    def _assign_request(
        self,
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None,
        extra_wishes: str | None,
        document_type: str,
    ) -> None:
        self.topic = topic
        self.volume_pages = volume_pages
        self.requirements = requirements
        self.extra_wishes = extra_wishes
        self.document_type = document_type

    def _assign_outcome(self, content: str | None, error_message: str | None) -> None:
        self.content = content
        self.error_message = error_message

    def _assign_retry_link(
        self,
        idempotency_key: str | None,
        source_generation_id: UUID | None,
        text_style: str | None,
    ) -> None:
        self.idempotency_key = idempotency_key
        self.source_generation_id = source_generation_id
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

    @staticmethod
    def _validated_create_fields(
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None,
        extra_wishes: str | None,
    ) -> str:
        """Apply every `create` bound, returning the topic narrowed to `str`."""
        topic = required_topic(topic)
        if len(topic) > MAX_TOPIC_LENGTH:
            raise ValidationException(TOPIC_TOO_LONG_MESSAGE)
        if is_out_of_range_volume(volume_pages):
            raise ValidationException(OUT_OF_RANGE_VOLUME_MESSAGE)
        if requirements is not None and len(requirements) > MAX_REQUIREMENTS_LENGTH:
            raise ValidationException(REQUIREMENTS_TOO_LONG_MESSAGE)
        if extra_wishes is not None and len(extra_wishes) > MAX_EXTRA_WISHES_LENGTH:
            raise ValidationException(EXTRA_WISHES_TOO_LONG_MESSAGE)
        return topic

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
        topic = cls._validated_create_fields(topic, volume_pages, requirements, extra_wishes)
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

        What is copied, what is re-validated, and why the two differ is set out
        under "CONSTRUCTION: `retry_of`" in the `generation_rules` docstring.
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
            text_style=_overridden_style(source, text_style),
            volume_pages=_overridden_volume(source, volume_pages),
        )
