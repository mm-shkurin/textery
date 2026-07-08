import unicodedata
from typing import Optional

from shared.exceptions import ValidationException

MISSING_TOPIC_MESSAGE = "topic is required"


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
        raise NotImplementedError()

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
