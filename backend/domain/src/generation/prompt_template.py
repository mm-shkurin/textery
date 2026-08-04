from document.document_type import (
    DOKLAD,
    ESSE,
    REFERAT,
    SOCHINENIE,
    SUPPORTED_DOCUMENT_TYPES,
)
from generation.generation import MAX_VOLUME_PAGES, MIN_VOLUME_PAGES
from shared.exceptions import DomainException

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


# The two refusal messages. They name the offending *field* and never interpolate
# its *value*: `generate_document.py` interpolates the caught error into the log, so
# a message quoting the rejected `topic` would put user text in the log through the
# error path.
VOLUME_PAGES_ERROR_MESSAGE = "volume_pages is not renderable in a prompt"
TOPIC_ERROR_MESSAGE = "topic is not renderable in a prompt"


class PromptBuildError(DomainException):
    """A prompt cannot be built from this request, and retrying will not help.

    Derives from the domain base rather than from `ValidationException`: the
    latter drags in `error_code`/`message` and the REST handler's 422 mapping,
    which is meaningless on a worker-only `BackgroundTask` path. The base being a
    domain exception is what lets the call site map every build failure to a
    terminal `fail()` instead of letting the catch-all retry a value that cannot
    change on attempt 2.
    """


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
        f"Напиши реферат на тему: {request.topic} ({request.volume_pages} стр.).\n"
        "Во введении обоснуй актуальность темы и сформулируй цель работы.\n"
        "В основной части раскрой разделы по теме.\n"
        "В заключении сформулируй выводы по проделанной работе."
    )


def _plain(request: PromptRequest) -> str:
    """The wording GigaChatProvider composes today, volume clause included.

    Byte-identical to `gigachat_provider.py`'s f-string, which is what makes the
    доклад golden a statement about the move rather than about a rewording. эссе
    and сочинение differ from the pre-refactor text by the ban line alone, which
    `build_prompt` appends -- they are in `TYPES_REQUIRING_SOURCE_BAN` and outside
    `_BAN_DEFERRED`.
    """
    return f"{request.document_type} на тему: {request.topic} ({request.volume_pages} стр.)"


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


def _is_renderable_volume(volume_pages) -> bool:
    """`bool` is excluded explicitly: `True` is an `int` and would render as `True стр.`."""
    if not isinstance(volume_pages, int) or isinstance(volume_pages, bool):
        return False
    return MIN_VOLUME_PAGES <= volume_pages <= MAX_VOLUME_PAGES


def _is_renderable_topic(topic) -> bool:
    return isinstance(topic, str) and topic.strip() != ""


def _reject_unrenderable_fields(request: PromptRequest) -> None:
    """Guards both fields before any template sees them.

    Checked here rather than inside `_plain`, which is the only template that
    interpolates `document_type`: a guard living in one template lets the other
    keep building from a request no caller should have been allowed to construct,
    and the hole is silent the day a type gets its own template. Both fields reach
    here unvalidated because `Generation.__init__` -- the storage hydration path --
    applies neither the range check nor the required-topic check that `create` does.
    """
    if not _is_renderable_volume(request.volume_pages):
        raise PromptBuildError(VOLUME_PAGES_ERROR_MESSAGE)
    if not _is_renderable_topic(request.topic):
        raise PromptBuildError(TOPIC_ERROR_MESSAGE)


def build_prompt(request: PromptRequest) -> str:
    """The prompt the model receives, ban included.

    The ban is appended here rather than inside each template so that its scope is
    the declared set and nothing else: a fifth long-form type joins
    SUPPORTED_DOCUMENT_TYPES and carries the ban with no human step, which is the
    whole point of deriving the scope instead of listing it.
    """
    _reject_unrenderable_fields(request)
    prompt = _TEMPLATES[request.document_type](request)
    if _requires_ban(request.document_type):
        return f"{prompt}\n{BAN_SENTENCE}"
    return prompt
