from typing import Protocol

from generation.generation import Generation


class ProviderError(Exception):
    pass


class GenerationProvider(Protocol):
    async def generate(self, generation: Generation) -> str: ...

    async def aclose(self) -> None:
        """Release whatever the implementation is holding open.

        On the port rather than discovered with `hasattr` at the composition root,
        because "does this provider need closing" is the adapter's answer to give
        and the caller should not have to ask. An implementation that holds
        nothing implements it as a no-op, which is a one-line honest answer rather
        than an absent method the shutdown path has to guess about.
        """
        ...
