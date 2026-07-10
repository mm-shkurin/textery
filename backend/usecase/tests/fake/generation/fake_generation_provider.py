from generation.generation import Generation


class FakeGenerationProvider:
    def __init__(self) -> None:
        self.content_to_return: str = ""
        self.error_to_raise: Exception | None = None
        self.received_generations: list[Generation] = []

    async def generate(self, generation: Generation) -> str:
        self.received_generations.append(generation)
        if self.error_to_raise is not None:
            raise self.error_to_raise
        return self.content_to_return
