from typing import Protocol


class HtmlSanitizer(Protocol):
    """Port for server-side HTML sanitization of document content.

    A port rather than a domain rule because the domain has no dependencies and
    cannot import a sanitizer. Allowlist-based by contract (the story requires
    "never a denylist"); the implementation is free to normalize markup, so the
    output is not guaranteed byte-identical to the input -- which is exactly why
    the save response must be built from what was stored, never echoed back from
    the request.
    """

    def sanitize(self, content: str) -> str:
        ...
