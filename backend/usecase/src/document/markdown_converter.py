from typing import Protocol


class MarkdownConverter(Protocol):
    """Port for turning an LLM's markdown answer into editor-shaped HTML.

    A port rather than a domain rule for the same reason HtmlSanitizer is one: the
    domain has no dependencies and cannot import a markdown parser.

    The contract is deliberately narrow -- one string in, one string out, no
    failure mode of its own. A converter that cannot parse its input has still
    been handed *text*, and the honest answer for unparseable markdown is the text
    itself wrapped in a paragraph, not an exception that would strand a completed
    generation the user already watched being written.

    The output is NOT sanitized and must not be treated as safe. Markdown permits
    raw embedded HTML, so anything the LLM emits between the fences reaches the
    converter's output unchanged; the caller runs it through HtmlSanitizer.
    Keeping the two separate is what lets the sanitizer stay the single control
    point for stored markup -- see CreateDocumentFromGeneration.
    """

    def to_html(self, markdown_text: str) -> str: ...
