class FakeGenerationProvider:
    """Stands in for `GenerationProvider`, and takes what that port takes.

    It received the `Generation` entity until scenario 2.1 moved prompt
    composition into the domain and narrowed the port to the composed string. The
    port changed; this double did not, and nothing noticed -- the usecase calls it
    through structural typing, so a double taking a different argument goes on
    passing every test while proving nothing about the real adapter. Recording
    the prompt is what the port now offers to record.
    """

    def __init__(self) -> None:
        self.content_to_return: str = ""
        self.error_to_raise: Exception | None = None
        self.fail_times: int | None = None
        self.received_prompts: list[str] = []
        self.call_count: int = 0
        self.closed: bool = False

    async def generate(self, prompt: str) -> str:
        self.received_prompts.append(prompt)
        self.call_count += 1
        if self.error_to_raise is not None and (
            self.fail_times is None or self.call_count <= self.fail_times
        ):
            raise self.error_to_raise
        return self.content_to_return

    async def aclose(self) -> None:
        """Holds nothing open, but implements the method anyway.

        A double that skips part of the port stops being a stand-in for it: mypy
        flagged exactly this when `aclose` was added, which is the check earning
        its keep -- the same drift that once let `FakeTokenService` quietly stop
        implementing `TokenService`.
        """
        self.closed = True
