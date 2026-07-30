import pytest

# Pure-Python, no native libs — but the dependency lands in the same commit as
# this suite, so guard collection rather than fail on a host that has not
# reinstalled requirements yet. Never a permanent skipif: the backend image and
# both CI test jobs install it, so this suite RUNS in every gating environment.
pytest.importorskip("markdown")

from rendering.markdown_html_converter import MarkdownHtmlConverter  # noqa: E402


@pytest.fixture
def converter():
    return MarkdownHtmlConverter()


class TestGeneratedMarkdownBecomesEditorShapedHtml:
    """The LLM answers in markdown; the editor and every export speak HTML.

    Each case below is a construct GigaChat actually emits in a Russian доклад —
    the untranslated conversion is what left `# Заголовок` rendering as a literal
    hash in the editor with the whole document collapsed into one paragraph.
    """

    @pytest.mark.parametrize(
        ("markdown_text", "expected"),
        [
            ("# Заголовок", "<h1>Заголовок</h1>"),
            ("## Введение", "<h2>Введение</h2>"),
            ("### Характеристики", "<h3>Характеристики</h3>"),
            ("Обычный абзац.", "<p>Обычный абзац.</p>"),
            ("Текст с **жирным**.", "<p>Текст с <strong>жирным</strong>.</p>"),
            ("Текст с *курсивом*.", "<p>Текст с <em>курсивом</em>.</p>"),
            ("> цитата", "<blockquote>\n<p>цитата</p>\n</blockquote>"),
        ],
    )
    def test_should_convert_a_construct_the_generator_emits(
        self, converter, markdown_text, expected
    ):
        assert converter.to_html(markdown_text) == expected

    def test_should_convert_a_bullet_list(self, converter):
        result = converter.to_html("- раз\n- два")

        assert result == "<ul>\n<li>раз</li>\n<li>два</li>\n</ul>"

    def test_should_convert_a_numbered_list(self, converter):
        result = converter.to_html("1. раз\n2. два")

        assert result == "<ol>\n<li>раз</li>\n<li>два</li>\n</ol>"

    def test_should_split_blank_line_separated_text_into_separate_paragraphs(self, converter):
        # The failure this whole conversion exists to fix: without it the editor
        # received one flat string and rendered the entire доклад as a single
        # unbroken block.
        result = converter.to_html("Первый абзац.\n\nВторой абзац.")

        assert result == "<p>Первый абзац.</p>\n<p>Второй абзац.</p>"


class TestHeadingsAreClampedToTheEditorSchema:
    """StarterKit is configured for levels 1–3, so a deeper heading has no node.

    Demoted rather than dropped: an <h4> the editor cannot load would dissolve
    into body text, silently flattening the document's structure.
    """

    @pytest.mark.parametrize("hashes", ["####", "#####", "######"])
    def test_should_demote_a_heading_deeper_than_the_editor_supports(self, converter, hashes):
        result = converter.to_html(f"{hashes} Подраздел")

        assert result == "<h3>Подраздел</h3>"

    def test_should_not_touch_a_heading_written_inside_a_code_fence(self, converter):
        # Why this is a tree processor and not a regex over the rendered HTML: a
        # string substitution would rewrite this fenced sample too.
        result = converter.to_html("```\n#### не заголовок\n```")

        assert "#### не заголовок" in result
        assert "<h3>" not in result


class TestOutputIsNotTrustedAsSafe:
    """The converter's contract ends at shape; safety is the caller's step.

    Markdown permits raw embedded HTML, so a payload in the LLM's answer reaches
    this output intact BY DESIGN. Pinned here so nobody later reads the absence of
    a test as evidence the converter is a security boundary and drops the
    sanitizer call in CreateDocumentFromGeneration.
    """

    def test_should_pass_embedded_html_through_untouched(self, converter):
        result = converter.to_html("<script>alert(1)</script>")

        assert "<script>alert(1)</script>" in result


class TestConverterIsTotal:
    """A completed generation must always yield something editable.

    The user watched this text being written. Any input that made the conversion
    raise would strand it behind an error instead — so there is no such input.
    """

    def test_should_return_empty_for_empty(self, converter):
        assert converter.to_html("") == ""

    def test_should_wrap_plain_unmarked_text_in_a_paragraph(self, converter):
        assert converter.to_html("просто текст") == "<p>просто текст</p>"

    def test_should_not_leak_state_between_conversions(self, converter):
        # A shared markdown.Markdown accumulates state across convert() calls.
        # This adapter is a process-lifetime singleton serving concurrent
        # requests, so a leak here is one document's structure appearing in
        # another's — invisible in a single-document test.
        first = converter.to_html("[ссылка][ref]\n\n[ref]: http://example.ru")
        second = converter.to_html("[ссылка][ref]")

        assert "http://example.ru" in first
        assert "http://example.ru" not in second, "the first call's reference link leaked"
