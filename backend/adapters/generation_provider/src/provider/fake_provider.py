FAKE_DOKLAD_TEXT = (
    "Введение\n\n"
    "Данный доклад посвящён теме, указанной пользователем. В работе рассматриваются "
    "ключевые аспекты предмета исследования, приводится анализ существующих подходов "
    "и формулируются основные выводы.\n\n"
    "Основная часть\n\n"
    "Тема раскрывается последовательно: сначала даётся общая характеристика вопроса, "
    "затем разбираются частные случаи и практические примеры, подтверждающие "
    "теоретические положения.\n\n"
    "Заключение\n\n"
    "В результате проведённого анализа можно сделать вывод о значимости рассмотренной "
    "темы и наметить направления для дальнейшего изучения."
)


class FakeProvider:
    async def generate(self, prompt: str) -> str:  # noqa: ARG002
        """The same text for every prompt.

        `prompt` is unread and deliberately still in the signature: the fake
        stands in for the port, and a fake whose shape drifts from the port stops
        being able to catch a caller that passes the wrong thing.
        """
        return FAKE_DOKLAD_TEXT

    async def aclose(self) -> None:
        """Nothing is held open. Present so the shutdown path can call the port
        uniformly instead of testing which implementation it was handed.
        """
        return None
