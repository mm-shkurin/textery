import unicodedata

MAX_CONTENT_LENGTH = 200_000


class DocumentContent:
    """Domain value object for a manual document's full editor content.

    Pipeline: raw cap -> NFC normalize -> re-cap. This mirrors Password/Email,
    and both caps are load-bearing rather than belt-and-braces: normalization is
    not length-preserving in either direction (NFD->NFC usually shrinks, but can
    grow in rare singleton/Hangul cases). The raw cap fails fast on an
    adversarial payload; the post-NFC cap is authoritative, because the
    normalized value is what gets sanitized and stored.

    The cap is measured in Unicode **code points** (Python's len), matching the
    `maxLength: 200000` in documents_save.yaml. An astral emoji counts as 1 --
    the surrogate-pair split that scenario 6.5 guards against is a JS/Java
    hazard, not Python's. Nothing is ever truncated, so no boundary can cut a
    character or grapheme in half: over-limit content is rejected whole.

    NFC normalization is also what makes scenario 6.2's duplicate-save
    comparison meaningful -- without it, NFD and NFC of the same visible text
    are two different strings and an identical resubmit would look like a change.

    The value is normalized but NOT sanitized: the domain has no dependencies,
    so it cannot import an HTML sanitizer. Sanitization is applied by the
    SaveDocument usecase via the HtmlSanitizer port.
    """

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str) or len(raw_value) > MAX_CONTENT_LENGTH:
            raise ValueError("Invalid content.")
        normalized_value = unicodedata.normalize("NFC", raw_value)
        if len(normalized_value) > MAX_CONTENT_LENGTH:
            raise ValueError("Invalid content.")
        self._value = normalized_value

    @property
    def value(self) -> str:
        return self._value
