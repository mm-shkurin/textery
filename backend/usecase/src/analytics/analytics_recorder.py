"""The port the product emits its own events through, and its silent default.

Five of the eight live events have no HTTP surface at all: they are emitted
in-process by the code that performed the transition they name, which is what
makes them unforgeable (`endpoints.md`, "One new endpoint, not a resource").

**Every method here is fail-open, and that is a contract, not an implementation
note.** A recorder that fails, refuses, or hangs must never change what the
observed operation answers -- that is the story's governing decision, and the
reason the return type is `None` with no exception in the signature: a caller
that cannot see a failure cannot react to one.

The implementation runs on its OWN database session, never the caller's. A
failed INSERT poisons the transaction it ran in, so sharing the product's
session would turn "analytics failed" into "the registration rolled back" --
precisely the outcome fail-open exists to prevent.
"""

import logging
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

logger = logging.getLogger(__name__)


class AnalyticsRecorder(Protocol):
    async def record(
        self,
        event_name: str,
        visitor_id: UUID | None,
        user_id: UUID | None,
        payload: dict[str, Any] | None = None,
        occurrence_key: UUID | None = None,
    ) -> None:
        """Record one server-emitted event. Never raises, never blocks for long.

        `occurrence_key` is the emitter's own dedupe key -- `occurrence_of(...)`
        derives one from the transition being reported -- so a completion
        reported twice from two instances collapses in the unique index rather
        than in a read the two instances would race on. `None` where the emitter
        has no natural subject; those rows sit outside the partial index and are
        deduped by the state transition that raised them instead.
        """
        ...


class NullAnalyticsRecorder:
    """The default when no recorder is wired -- unit tests, in-process harness.

    Records nothing and says nothing. A usecase constructed without a recorder
    must still run, for the same reason the real recorder swallows its own
    failures: the product does not depend on analytics working.
    """

    async def record(
        self,
        event_name: str,
        visitor_id: UUID | None,
        user_id: UUID | None,
        payload: dict[str, Any] | None = None,
        occurrence_key: UUID | None = None,
    ) -> None:
        logger.debug("analytics not wired; %s not recorded", event_name)


def occurrence_of(event_name: str, subject_id: object) -> UUID:
    """A stable dedupe key for one server-emitted transition.

    `uuid5`, so the same transition derives the same key on every instance and in
    every replica -- which is what lets the partial unique index collapse a
    double emission without any instance reading first. The namespace is the
    stock URL namespace over a scheme of our own: it needs to be constant and
    distinct, not secret, and a key that is guessable confers nothing (the
    column is unique per visitor and carries no authority).
    """
    return uuid5(NAMESPACE_URL, f"textery:analytics:{event_name}:{subject_id}")
