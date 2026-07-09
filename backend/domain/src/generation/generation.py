import unicodedata
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from shared.exceptions import ValidationException

MISSING_TOPIC_MESSAGE = "topic is required"
OUT_OF_RANGE_VOLUME_MESSAGE = "volume_pages must be between 1 and 10"
MIN_VOLUME_PAGES = 1
MAX_VOLUME_PAGES = 10
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

    def mark_in_progress(self) -> None:
        self.status = IN_PROGRESS_STATUS

    def complete(self, content: str) -> None:
        self.content = content
        self.status = COMPLETED_STATUS

    def fail(self, reason: str) -> None:
        self.status = FAILED_STATUS

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
        if cls._is_out_of_range_volume(volume_pages):
            raise ValidationException(OUT_OF_RANGE_VOLUME_MESSAGE)
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
