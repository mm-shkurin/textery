from typing import Protocol


class ProviderError(Exception):
    pass


class GenerationProvider(Protocol):
    async def generate(self, prompt: str) -> str:
        """Ask the model for a document, given the exact text to send.

        Takes the composed prompt rather than the `Generation`, so there is
        exactly ONE composer and it lives in the domain. While the provider built
        its own text from the entity, the domain's `build_prompt` was called by
        the usecase and its result thrown away: the реферат template and the
        invented-sources ban existed, were tested, and never reached the model.
        Two independently-editable definitions of the same prompt is a bug that
        cannot be caught by either one's golden.

        It also narrows what the adapter can see. A provider handed the entity can
        reach `owner_id`, `content` and `error_message`; a provider handed a string
        cannot.
        """
        ...

    async def aclose(self) -> None:
        """Release whatever the implementation is holding open.

        On the port rather than discovered with `hasattr` at the composition root,
        because "does this provider need closing" is the adapter's answer to give
        and the caller should not have to ask. An implementation that holds
        nothing implements it as a no-op, which is a one-line honest answer rather
        than an absent method the shutdown path has to guess about.
        """
        ...
