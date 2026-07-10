from generation.generation import Generation


class FakeGenerationProvider:
    def __init__(self) -> None:
        self.content_to_return: str = ""
        self.error_to_raise: Exception | None = None
        self.fail_times: int | None = None
        self.received_generations: list[Generation] = []
        self.call_count: int = 0

    async def generate(self, generation: Generation) -> str:
        self.received_generations.append(generation)
        self.call_count += 1
        if self.error_to_raise is not None and (self.fail_times is None or self.call_count <= self.fail_times):
            raise self.error_to_raise
        return self.content_to_return
