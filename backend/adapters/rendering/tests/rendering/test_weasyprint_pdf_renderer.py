import pytest

# WeasyPrint needs native Pango/cairo libs. Where they are absent (the bare dev
# host), skip this whole module at collection rather than error. The libs ARE
# installed in the backend image and on the CI runner (see backend.Dockerfile and
# ci.yml), so the test still executes in every gating environment -- the skip is
# "can't run here", never "silently never runs".
pytest.importorskip("weasyprint")

from document.export_format import ExportFormat  # noqa: E402
from rendering.weasyprint_pdf_renderer import WeasyPrintPdfRenderer  # noqa: E402


def test_should_render_html_to_real_pdf_bytes():
    result = WeasyPrintPdfRenderer().render("<p>Привет</p>", ExportFormat.PDF)

    # Strict adapter-level proof that WeasyPrint produced a genuine, COMPLETE PDF,
    # not merely a non-empty blob or an 8-byte header stub:
    #   - %PDF- : the file-format signature every valid PDF opens with;
    #   - %%EOF : the trailer every complete PDF closes with -- a truncated or
    #     header-only render would pass the prefix but fail here;
    #   - length floor: a real single-page render is kilobytes, so this pins
    #     against a header+trailer-only stub.
    # Full-body equality is deliberately not used -- WeasyPrint output is
    # non-deterministic (object order, timestamps, binary streams).
    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF-")
    assert result.rstrip().endswith(b"%%EOF")
    assert len(result) > 500
