import unicodedata
from datetime import UTC, datetime
from uuid import UUID, uuid4

from document.document_type import SUPPORTED_DOCUMENT_TYPES, DocumentType
from shared.exceptions import ValidationException

MIN_VOLUME_PAGES = 1
MAX_VOLUME_PAGES = 10
MAX_TOPIC_LENGTH = 500
MAX_REQUIREMENTS_LENGTH = 2000
MAX_EXTRA_WISHES_LENGTH = 2000

# Declared after the bounds and interpolated from them. These messages used to
# restate each number as a literal five lines from the constant it described, so
# changing a bound left the message quoting the old one -- the one place the
# discrepancy is guaranteed to be seen, by the user who just tripped the rule.
MISSING_TOPIC_MESSAGE = "topic is required"
OUT_OF_RANGE_VOLUME_MESSAGE = (
    f"volume_pages must be between {MIN_VOLUME_PAGES} and {MAX_VOLUME_PAGES}"
)
TOPIC_TOO_LONG_MESSAGE = f"topic must be at most {MAX_TOPIC_LENGTH} characters"
REQUIREMENTS_TOO_LONG_MESSAGE = f"requirements must be at most {MAX_REQUIREMENTS_LENGTH} characters"
EXTRA_WISHES_TOO_LONG_MESSAGE = f"extra_wishes must be at most {MAX_EXTRA_WISHES_LENGTH} characters"
INVALID_DOCUMENT_TYPE_MESSAGE = (
    f"document_type must be one of: {', '.join(SUPPORTED_DOCUMENT_TYPES)}"
)
PENDING_STATUS = "pending"
IN_PROGRESS_STATUS = "in_progress"
COMPLETED_STATUS = "completed"
FAILED_STATUS = "failed"


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
    ) -> "Generation":
        if cls._is_blank_topic(topic):
            raise ValidationException(MISSING_TOPIC_MESSAGE)
        if len(topic) > MAX_TOPIC_LENGTH:
            raise ValidationException(TOPIC_TOO_LONG_MESSAGE)
        if cls._is_out_of_range_volume(volume_pages):
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
            document_type=cls._validate_document_type(document_type),
        )

    @staticmethod
    def _validate_document_type(document_type: str) -> str:
        """Reject anything outside the four supported types.

        This factory validated topic, volume, requirements and extra_wishes and
        passed document_type straight through -- while Document.create ran the
        identical field through this same value object. So POST /documents
        rejected "реферат "; POST /generations accepted any string at all.

        It is not only an inconsistency. Unlike documents, the generations table
        carries no CHECK constraint on this column, so nothing downstream caught
        it either; and GigaChatProvider interpolates the value straight into the
        prompt ("{document_type} на тему: {topic}"). An unvalidated field that
        reaches an LLM prompt is an injection surface, and this one was the first
        word of it.

        DocumentType is reused rather than reimplemented: the allowlist is one
        tuple, and a second copy here would be the drift this commit is removing.
        """
        try:
            return DocumentType(document_type).value
        except ValueError as error:
            # error_code="INVALID_DOCUMENT_TYPE", matching CreateDocument, rather
            # than the bare VALIDATION_ERROR this factory's other rules raise. It
            # is the same field under the same allowlist, so a client that learned
            # to handle the code from /documents handles it here unchanged -- and
            # the shared handler already maps it to 422.
            raise ValidationException(
                error_code="INVALID_DOCUMENT_TYPE",
                message=INVALID_DOCUMENT_TYPE_MESSAGE,
            ) from error

    @staticmethod
    def _is_out_of_range_volume(volume_pages: int | None) -> bool:
        if volume_pages is None:
            return True
        return not (MIN_VOLUME_PAGES <= volume_pages <= MAX_VOLUME_PAGES)

    @staticmethod
    def _is_blank_topic(topic: str | None) -> bool:
        if topic is None:
            return True
        # str.strip() only removes Unicode whitespace (category Zs/Zl/Zp), not
        # format characters like U+200B ZERO WIDTH SPACE (category Cf). Strip
        # both ordinary whitespace and format characters before checking emptiness.
        visible_chars = [
            char for char in topic if not char.isspace() and unicodedata.category(char) != "Cf"
        ]
        return len(visible_chars) == 0
