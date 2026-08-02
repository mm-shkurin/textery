from document.document_type import (
    DOKLAD,
    ESSE,
    REFERAT,
    SOCHINENIE,
    SUPPORTED_DOCUMENT_TYPES,
)


class PromptRequest:
    """The narrow view of a generation a template is allowed to see.

    Deliberately not the `Generation` entity: `owner_id`, `content` and
    `error_message` are structurally unreachable from a template rather than
    merely unused by today's templates.
    """

    def __init__(self, document_type: str, topic: str) -> None:
        self.document_type = document_type
        self.topic = topic


def _referat(request: PromptRequest) -> str:
    """Each obligation gets its own sentence.

    A marker (`во введении`, `в заключении`) names its section exactly once, so
    the instruction attached to it is unambiguous both to the model and to the
    tests that read one sentence at a time.
    """
    return (
        f"Напиши реферат на тему: {request.topic}.\n"
        "Во введении обоснуй актуальность темы и сформулируй цель работы.\n"
        "В основной части раскрой разделы по теме.\n"
        "В заключении сформулируй выводы по проделанной работе."
    )


def _plain(request: PromptRequest) -> str:
    """The wording GigaChatProvider composes today, minus the volume clause.

    Kept as-is so that the goldens for доклад/эссе/сочинение (scenario 1.3) land
    against the pre-refactor text rather than against something invented here.
    """
    return f"{request.document_type} на тему: {request.topic}"


_TEMPLATES = {
    DOKLAD: _plain,
    ESSE: _plain,
    SOCHINENIE: _plain,
    REFERAT: _referat,
}

assert set(_TEMPLATES) == set(SUPPORTED_DOCUMENT_TYPES), (
    "every supported document type needs a prompt template"
)


def build_prompt(request: PromptRequest) -> str:
    return _TEMPLATES[request.document_type](request)
