import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime

import pytest

# htmldocx + python-docx are pure-Python (no native libs), so unlike the
# WeasyPrint suite these do not need Pango/cairo. But htmldocx is not yet a
# backend dependency (green-adapter adds it to requirements + CI), so guard the
# module at collection: skip where the parser is absent (the bare dev host and
# pre-green CI), run once it is installed. The skip is "can't run here", never
# "silently never runs".
pytest.importorskip("htmldocx")
pytest.importorskip("docx")

from document.export_format import ExportFormat  # noqa: E402

# A fixed instant injected into the renderer so docProps timestamps are the
# clock's value, not the machine's wall clock. Any drift between this constant
# and what core.xml carries proves raw system time leaked into the download.
FIXED_NOW = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)

# The only author identity the exported file may carry: a neutral product
# constant, never an OS/process username. If core.xml ever shows a real account
# name, the metadata-redaction guard (group-07 hazard) has regressed.
NEUTRAL_AUTHOR = "Textery"

_DC = "{http://purl.org/dc/elements/1.1/}"
_CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
_DCTERMS = "{http://purl.org/dc/terms/}"


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _core_xml(result: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert "docProps/core.xml" in archive.namelist()
        return archive.read("docProps/core.xml").decode("utf-8")


def _parsed_instant(text: str | None) -> datetime:
    assert text is not None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


@pytest.mark.skip(
    reason="RED: rendering.html_docx_renderer.HtmlDocxRenderer not implemented "
    "(ModuleNotFoundError on deferred import)"
)
class TestHtmlDocxRenderer:
    def test_should_render_html_to_real_docx_bytes(self):
        from rendering.html_docx_renderer import HtmlDocxRenderer  # noqa: E402

        result = HtmlDocxRenderer(clock=FixedClock(FIXED_NOW)).render(
            "<p>Привет</p>", ExportFormat.DOCX
        )

        # Strict proof this is a genuine OOXML .docx, not a non-empty blob:
        #   - PK\x03\x04 : the ZIP local-file-header signature every .docx opens with;
        #   - both [Content_Types].xml AND word/document.xml present in the archive:
        #     the two mandatory OOXML parts a real Word document must carry;
        #   - the input text survives in word/document.xml as multibyte UTF-8 --
        #     "Привет" pins that Cyrillic was not mangled/dropped on the way in.
        assert isinstance(result, bytes)
        assert result.startswith(b"PK\x03\x04")
        with zipfile.ZipFile(io.BytesIO(result)) as archive:
            names = archive.namelist()
            assert "[Content_Types].xml" in names
            assert "word/document.xml" in names
            document_xml = archive.read("word/document.xml").decode("utf-8")
        assert "Привет" in document_xml

    def test_should_write_neutral_docprops_without_server_identity_or_time(self):
        from rendering.html_docx_renderer import HtmlDocxRenderer  # noqa: E402

        result = HtmlDocxRenderer(clock=FixedClock(FIXED_NOW)).render(
            "<p>Привет</p>", ExportFormat.DOCX
        )

        root = ET.fromstring(_core_xml(result))
        # Author identity must be the neutral constant, never a real OS username.
        assert root.findtext(f"{_DC}creator") == NEUTRAL_AUTHOR
        assert root.findtext(f"{_CP}lastModifiedBy") == NEUTRAL_AUTHOR
        # Timestamps must be the INJECTED clock's instant, never raw wall clock.
        assert _parsed_instant(root.findtext(f"{_DCTERMS}created")) == FIXED_NOW
        assert _parsed_instant(root.findtext(f"{_DCTERMS}modified")) == FIXED_NOW
