"""The register the generated text is written in — научный / публицистический / художественный.

Its own module rather than three constants in `generation_rules`, on the same
grounds `DocumentType` is not a tuple of strings: the value is interpolated into
the prompt the model receives, so the allowlist and the sentence each member
turns into have to live together or one gets extended without the other.

Absence is a first-class member, spelled `None` and never a default value. A
generation created before this field existed has no style, and writing the
scientific register into those rows on read would claim the user chose it.
"""

from shared.exceptions import ValidationException

NAUCHNY = "научный"
PUBLICISTICHESKY = "публицистический"
HUDOZHESTVENNY = "художественный"

SUPPORTED_TEXT_STYLES = (NAUCHNY, PUBLICISTICHESKY, HUDOZHESTVENNY)

INVALID_TEXT_STYLE_MESSAGE = f"text_style must be one of: {', '.join(SUPPORTED_TEXT_STYLES)}"

# What each register asks the model for, as one sentence per style. Written out
# rather than derived from the label because "напиши в научном стиле" is the
# instruction a model follows least reliably: the useful part is the concrete
# properties, not the name of the register.
_STYLE_INSTRUCTIONS = {
    NAUCHNY: (
        "Пиши в научном стиле: выдержанная терминология, безличные конструкции, "
        "без разговорных оборотов и без обращений к читателю."
    ),
    PUBLICISTICHESKY: (
        "Пиши в публицистическом стиле: живая аргументация, обращение к читателю, "
        "конкретные примеры вместо отвлечённых формулировок."
    ),
    HUDOZHESTVENNY: (
        "Пиши в художественном стиле: образная речь, развёрнутые описания, "
        "разнообразный синтаксис вместо однотипных предложений."
    ),
}


def validate_text_style(text_style: str | None) -> str | None:
    """The style, proven to be one of the three, or `None` for "not chosen".

    `None` passes through rather than being rejected: the field is optional on
    the wire, and a request that names no style is a request for the model's own
    default register, which is what every generation made before this field
    existed already got.
    """
    if text_style is None:
        return None
    if text_style not in SUPPORTED_TEXT_STYLES:
        raise ValidationException(
            error_code="INVALID_TEXT_STYLE",
            message=INVALID_TEXT_STYLE_MESSAGE,
        )
    return text_style


def style_instruction(text_style: str | None) -> str | None:
    """The sentence a style adds to the prompt, or `None` when there is none.

    An unknown value answers `None` rather than raising. Validation happens at
    the edge; this is the prompt path, which also serves rows hydrated straight
    from storage — including a row written under an allowlist that has since
    changed. A style nobody recognises must degrade to "no style sentence", not
    take down a generation the user is waiting on.
    """
    if text_style is None:
        return None
    return _STYLE_INSTRUCTIONS.get(text_style)
