import pytest

from sanitization.nh3_html_sanitizer import Nh3HtmlSanitizer


@pytest.fixture
def sanitizer():
    return Nh3HtmlSanitizer()


class TestEditorFormattingSurvives:
    """Scenario 6.1: saved formatting must round-trip.

    The allowlist has to cover what the editor actually emits, or sanitization
    silently deletes users' work. Tiptap emits <strong>/<em>; scenario 6.1's own
    fixture pins <b>/<i>. Both are required — dropping either fails a test or
    corrupts real output.
    """

    @pytest.mark.parametrize(
        "markup",
        [
            "<h1>Заголовок</h1>",
            "<h2>Заголовок</h2>",
            "<h3>Заголовок</h3>",
            "<p>Абзац</p>",
            "<ul><li>пункт</li></ul>",
            "<ol><li>пункт</li></ol>",
            "<strong>жирный</strong>",
            "<em>курсив</em>",
            "<b>жирный</b>",
            "<i>курсив</i>",
            "<u>подчёркнутый</u>",
            "<p>строка<br>перенос</p>",
            # The block half of the StarterKit schema story 5 migrated the editor
            # to. Each of these has a toolbar button (Цитата, Блок кода,
            # горизонтальная линейка, зачёркивание), and each was stripped on save
            # until the allowlist caught up — the user formatted, saved, reloaded,
            # and found a bare paragraph. Markdown conversion emits the same tags.
            "<blockquote><p>Цитата</p></blockquote>",
            "<pre><code>print(1)</code></pre>",
            "<p>до</p><hr><p>после</p>",
            "<p><s>вычеркнуто</s></p>",
            "<p><code>inline</code></p>",
        ],
    )
    def test_should_preserve_allowed_formatting(self, sanitizer, markup):
        assert sanitizer.sanitize(markup) == markup, f"{markup} must survive sanitization unchanged"

    def test_should_normalize_a_self_closing_break_to_html5(self, sanitizer):
        # nh3 is an HTML5 tree parser and re-serializes: `<br />` comes back `<br>`.
        # Pinned rather than worked around -- it is a live example of why
        # documents_get.yaml says the stored content is "not necessarily
        # byte-identical to what was submitted", and why the PUT response must be
        # built from what was stored rather than echoed from the request.
        assert sanitizer.sanitize("<p>a<br />b</p>") == "<p>a<br>b</p>"

    def test_should_preserve_a_cyrillic_multi_paragraph_document(self, sanitizer):
        # Scenario 6.4: an entirely Cyrillic document round-trips without corruption.
        markup = "<h1>Доклад</h1><p>Первый абзац.</p><ul><li>Раз</li><li>Два</li></ul>"

        assert sanitizer.sanitize(markup) == markup


class TestExecutableMarkupIsNeutralized:
    """Scenario 7.1 / Security 1.1: raw script and event handlers are neutralized."""

    def test_should_remove_a_script_tag_together_with_its_contents(self, sanitizer):
        # Contents too, not just the tag: leaving "alert(1)" as bare text would
        # technically be "stripped" while still dumping the payload into the document.
        result = sanitizer.sanitize("<p>ok</p><script>alert(1)</script>")

        assert result == "<p>ok</p>", f"script and its body must both go, got {result!r}"
        assert "alert" not in result

    def test_should_drop_an_event_handler_attribute_but_keep_the_text(self, sanitizer):
        result = sanitizer.sanitize('<div onclick="steal()">текст</div>')

        assert "onclick" not in result, f"event handlers must not survive, got {result!r}"
        assert "steal" not in result
        assert "текст" in result, "the user's text must survive an unknown wrapper tag"

    def test_should_drop_an_image_with_an_onerror_payload(self, sanitizer):
        result = sanitizer.sanitize('<img src="x" onerror="alert(1)">')

        assert "onerror" not in result
        assert "alert" not in result

    def test_should_drop_a_style_tag_with_its_contents(self, sanitizer):
        result = sanitizer.sanitize("<p>ok</p><style>body{display:none}</style>")

        assert "display:none" not in result, f"style body must not survive, got {result!r}"


class TestLinks:
    """The link allowlist must match the editor's, or a user's link vanishes on reload."""

    def test_should_keep_an_http_link_and_force_a_safe_rel(self, sanitizer):
        result = sanitizer.sanitize('<a href="http://example.ru">ссылка</a>')

        assert 'href="http://example.ru"' in result
        assert "noopener" in result, "rel must be forced server-side, not trusted from the client"
        assert "ссылка" in result

    @pytest.mark.parametrize(
        "href",
        ["https://example.ru", "mailto:a@example.ru", "tel:+70000000000", "ftp://example.ru"],
    )
    def test_should_keep_every_protocol_the_editor_permits(self, sanitizer, href):
        # The client (Tiptap) allows these; if the server dropped one, a user would
        # create the link, see it render, save, reload — and find it gone.
        result = sanitizer.sanitize(f'<a href="{href}">x</a>')

        assert href in result, f"{href} must survive; the editor lets users create it"

    def test_should_drop_a_javascript_url(self, sanitizer):
        result = sanitizer.sanitize('<a href="javascript:alert(1)">click</a>')

        assert "javascript" not in result, f"javascript: URLs must not survive, got {result!r}"
        assert "click" in result, "the link text survives; only the href is dropped"


class TestSanitizerIsTotal:
    def test_should_return_empty_for_empty(self, sanitizer):
        assert sanitizer.sanitize("") == ""

    def test_should_escape_bare_angle_brackets_rather_than_dropping_text(self, sanitizer):
        # Escaping GROWS the string — which is why the 200,000-character cap is
        # measured before sanitization, not after.
        result = sanitizer.sanitize("<p>a &lt; b</p>")

        assert "a &lt; b" in result


class TestTextAlignmentSurvivesButOtherCssDoesNot:
    """`style` is allowed on block tags for ONE property: text alignment.

    nh3 filters tags, attributes and URL schemes but does not parse CSS, so
    letting `style` through unexamined would hand over the whole property space.
    The attribute filter is an allowlist of one property and four values; these
    tests pin both halves, because a filter that only kept the good cases (or only
    dropped the bad ones) would pass half of them.
    """

    @pytest.mark.parametrize("alignment", ["left", "right", "center", "justify"])
    def test_should_preserve_every_alignment_the_editor_can_set(self, sanitizer, alignment):
        markup = f'<p style="text-align: {alignment}">текст</p>'

        assert sanitizer.sanitize(markup) == markup

    @pytest.mark.parametrize(
        "style",
        [
            "position: fixed; top: 0",
            "background: url(http://evil.example/x)",
            "display: none",
            # The salvage trap: a real alignment with a payload riding along. The
            # whole attribute is dropped rather than the good half kept, so no
            # partial honouring can smuggle the second declaration through.
            "text-align: center; position: fixed",
            # Not an alignment the editor can produce, so not one worth risking a
            # value the CSS parser might read differently than this filter does.
            "text-align: url(javascript:alert(1))",
        ],
    )
    def test_should_drop_any_style_that_is_not_a_plain_alignment(self, sanitizer, style):
        result = sanitizer.sanitize(f'<p style="{style}">текст</p>')

        assert result == "<p>текст</p>", f"{style!r} must not survive, got {result!r}"

    def test_should_keep_the_paragraph_text_when_it_drops_the_style(self, sanitizer):
        # Dropping the attribute must never drop the user's words with it.
        result = sanitizer.sanitize('<p style="position: fixed">важный текст</p>')

        assert "важный текст" in result
