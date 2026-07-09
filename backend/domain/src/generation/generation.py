import unicodedata
from typing import Optional

from shared.exceptions import ValidationException

MISSING_TOPIC_MESSAGE = "topic is required"
OUT_OF_RANGE_VOLUME_MESSAGE = "volume_pages must be between 1 and 10"
MIN_VOLUME_PAGES = 1
MAX_VOLUME_PAGES = 10


class Generation:
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
        raise NotImplementedError()

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
