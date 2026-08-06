"""One function per document type: the text each one asks the model for.

Split out of `prompt_template.py` when эссе and сочинение stopped sharing the
plain template and pushed that file past the 200-line cap. The composition rules
that apply to *every* type -- the field guards, the source ban, the template
lookup -- stay there; what a single type says lives here.

Shared contract, inherited from `_referat` and honoured by all four: one
obligation per sentence, and a section marker (`во вступлении`, `в заключении`)
named exactly once, so each instruction is unambiguous to the model and readable
one sentence at a time by the goldens.
"""

from document.document_type import DOKLAD, ESSE, REFERAT, SOCHINENIE
from generation.prompt_request import PromptRequest


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


def _esse(request: PromptRequest) -> str:
    """Эссе — a reasoned personal position, not a survey of one.

    Same one-obligation-per-sentence contract as `_referat`, and the same reason:
    a section marker (`во вступлении`, `в заключении`) appears exactly once, so
    each instruction is unambiguous to the model and readable one sentence at a
    time by the goldens.

    What distinguishes it from реферат is asked for explicitly. Эссе is the one
    type where the author's own stance is the point, and a model given only "эссе
    на тему X" reliably returns an encyclopedia entry -- the failure this template
    exists to remove.
    """
    return (
        f"Напиши эссе на тему: {request.topic} ({request.volume_pages} стр.).\n"
        "Во вступлении сформулируй тезис — собственную позицию по теме.\n"
        "В основной части приведи аргументы в поддержку тезиса и рассмотри "
        "возражение против него.\n"
        "В заключении вернись к тезису и подведи итог рассуждения."
    )


def _sochinenie(request: PromptRequest) -> str:
    """Сочинение — a school essay: an argued answer, examples carrying the weight.

    Deliberately not a synonym of `_esse`. Эссе argues a personal thesis and is
    judged on the reasoning; сочинение answers the question the topic poses and is
    judged on whether the examples support the answer. Collapsing the two onto one
    template would make the type choice cosmetic, which is precisely what the
    plain template did.
    """
    return (
        f"Напиши сочинение на тему: {request.topic} ({request.volume_pages} стр.).\n"
        "Во вступлении объясни, как ты понимаешь тему, и сформулируй основную мысль.\n"
        "В основной части раскрой основную мысль и подкрепи её примерами.\n"
        "В заключении сформулируй вывод, который следует из приведённых примеров."
    )


def _plain(request: PromptRequest) -> str:
    """The wording GigaChatProvider composed before prompts moved into the domain.

    Byte-identical to the f-string that adapter carried, which is what makes the
    доклад golden a statement about the move rather than about a rewording.

    доклад is now its only user. эссе and сочинение had it because they had no
    template of their own, not because a bare noun phrase was the right prompt for
    them; each has one now. доклад keeps it until story 1 lands — see
    `_BAN_DEFERRED` for the same freeze and the same unblock condition.
    """
    return f"{request.document_type} на тему: {request.topic} ({request.volume_pages} стр.)"


# Public: `prompt_template.build_prompt` looks a type up here, and
# `test_prompt_type_coverage.py` asserts the table covers SUPPORTED_DOCUMENT_TYPES.
TEMPLATES = {
    DOKLAD: _plain,
    ESSE: _esse,
    SOCHINENIE: _sochinenie,
    REFERAT: _referat,
}


