from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RawResponseDto:
    """An HTTP response kept in its wire form.

    `text` is the undecoded response body. Scenario 1.1 asserts two 404 bodies are
    *byte-identical*, which a parsed dict cannot express: `{"a": 1, "b": 2}` and
    `{"b": 2, "a": 1}` compare equal as dicts while differing on the wire, and a
    difference in whitespace or key order is exactly the kind of accidental tell
    that distinguishes an absent document from a foreign one.
    """

    status_code: int
    text: str
    body: Optional[dict]
