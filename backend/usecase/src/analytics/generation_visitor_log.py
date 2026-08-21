"""Remembering which browser asked for a generation, and its silent default.

A generation is requested by a browser and completes minutes later, in a
background task, possibly on another instance (§9.2). Without this the
completion event carries no visitor and the funnel breaks exactly where it is
most interesting -- between "asked for a document" and "got one".

Fail-open on BOTH sides, like everything else in this story: `remember` that
fails loses the join for one generation, and `visitor_of` that fails answers
`None`, which the column already accepts.
"""

import logging
from typing import Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


class GenerationVisitorLog(Protocol):
    async def remember(self, generation_id: UUID, visitor_id: UUID | None) -> None:
        """Record the requesting browser. Never raises."""
        ...

    async def visitor_of(self, generation_id: UUID) -> UUID | None:
        """The requesting browser, or `None`. Never raises."""
        ...


class NullGenerationVisitorLog:
    async def remember(self, generation_id: UUID, visitor_id: UUID | None) -> None:
        logger.debug("generation visitor log not wired; nothing remembered")

    async def visitor_of(self, generation_id: UUID) -> UUID | None:
        return None
