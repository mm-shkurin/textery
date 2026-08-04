from document.document_type import (
    DOKLAD,
    ESSE,
    REFERAT,
    SOCHINENIE,
    SUPPORTED_DOCUMENT_TYPES,
)

# Every supported type requires the ban: the harm (a student submits a document
# carrying invented sources) does not depend on which type was asked for. Written
# as a derivation rather than a hand-listed tuple on purpose -- a hand-maintained
# list is forgotten by the same developer who forgets to wire the ban into a fifth
# type's template, which defeats the guard it is supposed to be.
TYPES_REQUIRING_SOURCE_BAN = SUPPORTED_DOCUMENT_TYPES

# A scheduling freeze, not a judgement about доклад: story 1 is being finished in
# textery-editor / textery-projects against today's доклад output, so changing that
# text now reddens their tests for a reason unrelated to their work. The unblock
# condition is story 1 landing; the follow-up belongs to scenario 2.1.
_BAN_DEFERRED = (DOKLAD,)

# Its own sentence on its own line, last, consistent with `_referat`'s
# one-marker-per-section contract -- folded into a neighbouring sentence it would
# still satisfy a substring check while losing the position the guard asserts.
BAN_SENTENCE = "Не включай список литературы и не ссылайся на источники."


class PromptRequest:
    """The narrow view of a generation a template is allowed to see.

    Deliberately not the `Generation` entity: `owner_id`, `content` and
    `error_message` are structurally unreachable from a template rather than
    merely unused by today's templates.
    """

    def __init__(self, document_type: str, topic: str, volume_pages: int) -> None:
        self.document_type = document_type
        self.topic = topic
        self.volume_pages = volume_pages


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


def _requires_ban(document_type: str) -> bool:
    return document_type in TYPES_REQUIRING_SOURCE_BAN and document_type not in _BAN_DEFERRED


def build_prompt(request: PromptRequest) -> str:
    """The prompt the model receives, ban included.

    The ban is appended here rather than inside each template so that its scope is
    the declared set and nothing else: a fifth long-form type joins
    SUPPORTED_DOCUMENT_TYPES and carries the ban with no human step, which is the
    whole point of deriving the scope instead of listing it.
    """
    prompt = _TEMPLATES[request.document_type](request)
    if _requires_ban(request.document_type):
        return f"{prompt}\n{BAN_SENTENCE}"
    return prompt
