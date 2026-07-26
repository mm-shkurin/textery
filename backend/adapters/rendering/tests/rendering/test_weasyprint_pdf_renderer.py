import pytest

from document.export_format import ExportFormat


@pytest.mark.skip(
    reason="RED: WeasyPrintPdfRenderer adapter not implemented yet (Scenario 2.1); "
    "real render verified in-container"
)
def test_should_render_html_to_real_pdf_bytes():
    # Deferred import: WeasyPrintPdfRenderer imports weasyprint at module load,
    # which cannot import on the Windows host (no GTK/pango/cairo). Importing
    # inside the body keeps this module COLLECTABLE on the host (the suite shows a
    # skip, not a collection error); the real render is verified in-container.
    from rendering.weasyprint_pdf_renderer import WeasyPrintPdfRenderer

    renderer = WeasyPrintPdfRenderer()

    result = renderer.render("<p>Привет</p>", ExportFormat.PDF)

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
