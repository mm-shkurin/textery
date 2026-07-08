from typing import Optional


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
        raise NotImplementedError()
