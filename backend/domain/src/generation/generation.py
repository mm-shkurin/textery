import unicodedata
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from shared.exceptions import ValidationException

MISSING_TOPIC_MESSAGE = "topic is required"
OUT_OF_RANGE_VOLUME_MESSAGE = "volume_pages must be between 1 and 10"
TOPIC_TOO_LONG_MESSAGE = "topic must be at most 500 characters"
REQUIREMENTS_TOO_LONG_MESSAGE = "requirements must be at most 2000 characters"
EXTRA_WISHES_TOO_LONG_MESSAGE = "extra_wishes must be at most 2000 characters"
MIN_VOLUME_PAGES = 1
MAX_VOLUME_PAGES = 10
MAX_TOPIC_LENGTH = 500
MAX_REQUIREMENTS_LENGTH = 2000
MAX_EXTRA_WISHES_LENGTH = 2000
PENDING_STATUS = "pending"
IN_PROGRESS_STATUS = "in_progress"
COMPLETED_STATUS = "completed"
FAILED_STATUS = "failed"


class Generation:
    def __init__(
        self,
        id: UUID,
        status: str,
        created_at: datetime,
        topic: Optional[str],
        volume_pages: Optional[int],
        requirements: Optional[str],
        extra_wishes: Optional[str],
        document_type: str,
        content: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        self.id = id
        self.status = status
        self.created_at = created_at
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
        topic: Optional[str],
        volume_pages: Optional[int],
        requirements: Optional[str],
        extra_wishes: Optional[str],
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
            status=PENDING_STATUS,
            created_at=datetime.now(timezone.utc),
            topic=topic,
            volume_pages=volume_pages,
            requirements=requirements,
            extra_wishes=extra_wishes,
            document_type=document_type,
        )

    @staticmethod
    def _is_out_of_range_volume(volume_pages: Optional[int]) -> bool:
        if volume_pages is None:
            return True
        return not (MIN_VOLUME_PAGES <= volume_pages <= MAX_VOLUME_PAGES)

    @staticmethod
    def _is_blank_topic(topic: Optional[str]) -> bool:
        if topic is None:
            return True
        # str.strip() only removes Unicode whitespace (category Zs/Zl/Zp), not
        # format characters like U+200B ZERO WIDTH SPACE (category Cf). Strip
        # both ordinary whitespace and format characters before checking emptiness.
        visible_chars = [
            char for char in topic
            if not char.isspace() and unicodedata.category(char) != "Cf"
        ]
        return len(visible_chars) == 0
