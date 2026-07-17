from typing import Protocol
from uuid import UUID


class DocumentGenerator(Protocol):
    """Runs a submitted generation to completion.

    GenerateDocument is the implementation, but it is not the only one: the
    composition root wires a wrapper that opens its own session per call, because
    the request's session is already closed by the time BackgroundTasks runs the
    job. That wrapper is not a GenerateDocument and does not subclass one, so the
    factory annotated `-> GenerateDocument` was simply false -- only duck typing
    kept it working, and a type checker reading the composition root would have
    been told something untrue about what it builds.

    Declaring the shape both satisfy makes the annotation honest and names what
    the router actually depends on: something you can hand a (generation_id,
    owner_id) to. The router has no business knowing whether that runs inline or
    on its own session.
    """

    async def execute(self, generation_id: UUID, owner_id: UUID) -> None: ...
