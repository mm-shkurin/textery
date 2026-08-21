"""What survives a save when the editor's «вставить таблицу» control was used.

Its own module rather than more cases in `test_nh3_html_sanitizer`: that file is about the XSS
boundary, and these are about DATA LOSS — a tag the editor can produce but the sanitizer strips is
silent loss the user discovers on reload, which is a different failure with a different fix.
"""

from sanitization.nh3_html_sanitizer import Nh3HtmlSanitizer

TABLE = (
    "<table><tbody>"
    "<tr><th>Год</th><th>Событие</th></tr>"
    "<tr><td>1961</td><td>Первый полёт человека в космос</td></tr>"
    "</tbody></table>"
)


class TestTablesSurviveASave:
    def test_should_keep_every_structural_tag_of_a_table(self):
        cleaned = Nh3HtmlSanitizer().sanitize(TABLE)

        for tag in ("<table>", "<tbody>", "<tr>", "<th>", "<td>"):
            assert tag in cleaned, (
                f"{tag} is stripped, so a saved table comes back as unwrapped cell text"
            )

    def test_should_keep_the_cell_text(self):
        cleaned = Nh3HtmlSanitizer().sanitize(TABLE)

        assert "Первый полёт человека в космос" in cleaned

    def test_should_keep_merged_cell_spans(self):
        cleaned = Nh3HtmlSanitizer().sanitize(
            '<table><tbody><tr><td colspan="2" rowspan="3">x</td></tr></tbody></table>'
        )

        # Losing a span does not degrade the table, it corrupts its shape: the remaining cells
        # shift into the columns the merge was covering.
        assert 'colspan="2"' in cleaned
        assert 'rowspan="3"' in cleaned

    def test_should_drop_a_style_attribute_from_a_cell(self):
        # `style` is allowed on the block nodes that carry text alignment and nowhere else. A cell
        # is not on that list, so the whole property space stays closed here.
        cleaned = Nh3HtmlSanitizer().sanitize(
            '<table><tbody><tr><td style="position: fixed">x</td></tr></tbody></table>'
        )

        assert "position" not in cleaned

    def test_should_still_strip_a_script_hidden_inside_a_cell(self):
        cleaned = Nh3HtmlSanitizer().sanitize(
            "<table><tbody><tr><td><script>alert(1)</script>ок</td></tr></tbody></table>"
        )

        # Removed WITH its contents: dropping only the tag would leave `alert(1)` sitting in the
        # document as text — technically stripped, still the payload.
        assert "script" not in cleaned
        assert "alert(1)" not in cleaned
        assert "ок" in cleaned


class TestImagesAreNotAdmitted:
    def test_should_strip_an_image_rather_than_store_one_the_exports_cannot_render(self):
        cleaned = Nh3HtmlSanitizer().sanitize('<p>до</p><img src="https://example.com/a.png">')

        # A deliberate refusal, not an oversight. Both export renderers block outbound fetches
        # (the document HTML is user-controlled, so resolving a src is an SSRF vector), so an
        # allowed <img> would render in the editor and vanish from every downloaded PDF and DOCX.
        assert "<img" not in cleaned
        assert "<p>до</p>" in cleaned
