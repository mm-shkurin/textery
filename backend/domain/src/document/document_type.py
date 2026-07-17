import unicodedata

DOKLAD = "доклад"
ESSE = "эссе"
SOCHINENIE = "сочинение"
REFERAT = "реферат"

SUPPORTED_DOCUMENT_TYPES = (DOKLAD, ESSE, SOCHINENIE, REFERAT)


class DocumentType:
    """Domain value object for a manual document's type.

    The allowlist lives here rather than in the request DTO: the DB check
    constraint and the REST layer both derive from these constants, so the four
    supported values are single-sourced. Matching is exact after NFC
    normalization -- deliberately case-sensitive, since these are fixed protocol
    values the client picks from an enum, not free text a user types.
    """

    def __init__(self, raw_value: str) -> None:
        if not isinstance(raw_value, str):
            raise ValueError("Invalid document type.")
        normalized_value = unicodedata.normalize("NFC", raw_value)
        if normalized_value not in SUPPORTED_DOCUMENT_TYPES:
            raise ValueError("Invalid document type.")
        self._value = normalized_value

    @property
    def value(self) -> str:
        return self._value
