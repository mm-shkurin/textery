import markdown
from markdown.treeprocessors import Treeprocessor

# The deepest heading the editor's schema can hold. StarterKit is configured with
# `heading: {levels: [1, 2, 3]}` (useManualEditorInstance.ts), so an <h4> has no
# node to load into: Tiptap drops the tag and keeps the text as a loose paragraph,
# and the sanitizer would have unwrapped it first anyway. Demoting is the lossless
# answer -- the text stays a heading, one level shallower, instead of dissolving
# into the body of the document.
_DEEPEST_SUPPORTED_HEADING = 3
_HEADING_TAGS = {f"h{level}": level for level in range(1, 7)}

# `extra` brings fenced code blocks and tables; `sane_lists` stops a list from
# swallowing the paragraph that follows it. Nothing here enables raw-HTML
# passthrough on purpose -- markdown allows embedded HTML regardless, which is
# precisely why the caller sanitizes the output.
_EXTENSIONS = ["extra", "sane_lists"]


class _DemoteDeepHeadings(Treeprocessor):
    """Clamp h4-h6 to the deepest heading the editor can represent.

    A tree processor rather than a regex over the rendered HTML: this runs on the
    parsed document, so it cannot mistake the text `<h4>` inside a code fence for
    a real heading the way a string substitution would.
    """

    def run(self, root):
        for element in root.iter():
            level = _HEADING_TAGS.get(element.tag)
            if level is not None and level > _DEEPEST_SUPPORTED_HEADING:
                element.tag = f"h{_DEEPEST_SUPPORTED_HEADING}"
        return root


class _EditorSchemaExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md: markdown.Markdown) -> None:
        # After `inline` (5) and before the serializer, at a priority no built-in
        # processor claims. Ordering only matters against other tree processors,
        # and none of the enabled extensions rewrites heading tags.
        md.treeprocessors.register(_DemoteDeepHeadings(md), "demote_deep_headings", 4)


class MarkdownHtmlConverter:
    """MarkdownConverter port implementation, backed by Python-Markdown.

    Lives beside the PDF and DOCX renderers because it is the same kind of thing:
    a format conversion at the system's edge, isolated behind a port so the
    usecase never imports a parser.

    Output is editor-shaped but NOT safe: markdown permits raw embedded HTML, so
    a `<script>` in the LLM's answer reaches this output intact. Sanitization is
    the caller's step and deliberately not folded in here -- one control point for
    stored markup is auditable, two are a question about which one ran.
    """

    def to_html(self, markdown_text: str) -> str:
        # A fresh parser per call. `markdown.Markdown` accumulates state across
        # `convert()` (it exposes `reset()` for exactly that reason), and this
        # adapter is a process-lifetime singleton serving concurrent requests --
        # a shared instance would let one document's footnotes and reference
        # links bleed into another's. Construction is microseconds; the bug it
        # avoids is silent cross-request contamination.
        parser = markdown.Markdown(extensions=[*_EXTENSIONS, _EditorSchemaExtension()])
        return parser.convert(markdown_text)
