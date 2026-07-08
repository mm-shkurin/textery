from typing import Optional

from generation.generation import Generation


class RequestGeneration:
    """Orchestrates submission of a new generation request.

    Scenario 1.1 scope: delegate field validation to the domain factory,
    letting ValidationException propagate uncaught. No persistence or
    success path yet -- Generation.create() itself still raises
    NotImplementedError for a valid topic.
    """

    async def execute(
        self,
        topic: Optional[str],
        volume_pages: Optional[int],
        requirements: Optional[str],
        extra_wishes: Optional[str],
        document_type: str,
    ) -> Generation:
        return Generation.create(
            topic=topic,
            volume_pages=volume_pages,
            requirements=requirements,
            extra_wishes=extra_wishes,
            document_type=document_type,
        )
