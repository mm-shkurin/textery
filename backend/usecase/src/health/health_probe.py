from typing import Protocol


class HealthProbe(Protocol):
    """Port for asking a downstream dependency whether it is actually reachable.

    A port rather than a direct engine call from the router, for the usual reason:
    `adapters/rest` cannot import `adapters/db`, and the check has to touch the
    database to be worth anything. The usecase depends on this; the db adapter
    implements it.

    Deliberately narrow. It answers reachability, not correctness -- no schema
    version, no row counts, no migration state. A health probe that asserts more
    than "the connection works" starts failing for reasons that are not outages,
    and an orchestrator that restarts a container over one of those turns a
    non-event into downtime.
    """

    async def ping(self) -> None:
        """Return normally if the dependency answered; raise otherwise.

        No boolean: the failure carries a driver exception that names what went
        wrong, and collapsing it to `False` at the port would throw that away
        exactly where it is needed. The usecase catches and logs it.
        """
        ...
