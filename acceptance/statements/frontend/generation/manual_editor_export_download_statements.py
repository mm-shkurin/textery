"""Statements for scenario 5.1 — a successful PDF export delivers a downloaded file.

The spec's payoff (17 UI Tests §5.1): a real export must not just fetch bytes and drop them —
the browser must receive a FILE. Today `exportDocument` resolves a Blob through the shared
transport (2.1 green-frontend-api), but ExportControl.tsx:78 awaits that Blob and discards it —
no object-URL anchor click, no `download` attribute — so nothing lands on disk. green-frontend 5.1
adds the blob->download delivery; green-selenium removes the skip and runs this live.

Split out of manual_editor_export_control_statements.py (already near the 200-line limit) to keep
both files under the cap. `ExportDownloadStatementsMixin` is mixed into `ExportControlStatements`,
so the same `export_control_statements` fixture exposes these helpers.

Headless Chrome will not write downloads unless told to: the webdriver fixture (conftest.py) sets
no download dir, so `enable_download_capture` opts in via CDP `Page.setDownloadBehavior` with a
per-test temp dir. The assertion then polls that dir for a COMPLETE file — a real, non-empty file
present, not a `.crdownload` partial and not merely a non-empty directory — which is the only
browser-observable proof that the exported bytes reached the user rather than being dropped.
"""

import os
import tempfile
import time

from statements.frontend.base_frontend_statements import WAIT_TIMEOUT_SECONDS
from statements.frontend.generation.export_control_locators import EXPORT_OPTION_PDF

# Chrome writes an in-progress download as `<name>.crdownload` and renames it to the final name
# only once every byte has arrived. Treating a `.crdownload` as success would pass on a truncated
# or still-streaming file, so the completion check excludes this suffix.
_PARTIAL_DOWNLOAD_SUFFIX = ".crdownload"

# The download lands after the export GET resolves and Chrome flushes the blob to disk, which lags
# the PDF-option click. Poll the capture dir until a complete file appears or the shared wait
# timeout elapses.
_POLL_INTERVAL_SECONDS = 0.25

# The scenario exports "as pdf", so the delivered download is a PDF file — a category-1 value the
# test defines. Completion detection stays format-agnostic (so a wrong-format download yields a
# clear "not a PDF" failure instead of a timeout), and the exported file's extension is asserted
# explicitly here.
_EXPORTED_PDF_SUFFIX = ".pdf"


class ExportDownloadStatementsMixin:
    """5.1 helpers: capture browser downloads, trigger a PDF export, assert a file was delivered."""

    def enable_download_capture(self, driver) -> None:
        """Point headless Chrome's downloads at a fresh per-test temp dir via CDP.

        The webdriver fixture enables no download behavior, so without this every download is
        blocked and the assertion would time out regardless of whether the app delivers the blob.
        `Page.setDownloadBehavior` with `behavior=allow` writes completed downloads into
        `downloadPath`; the dir is stored on the instance so the assertion knows where to look.
        """
        self._download_dir = tempfile.mkdtemp(prefix="textery-export-5-1-")
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": self._download_dir},
        )

    def trigger_pdf_export_for_download(self, driver) -> None:
        """Open the export control and click the PDF choice once, with no network throttle.

        Opening the control is a local toggle (no request); the GET /export fires only on this PDF
        click. No throttle here — unlike the in-flight scenarios we WANT the export to complete so
        Chrome flushes the returned blob to the capture dir as a file.
        """
        self.open_export_control(driver)
        self._wait_for_visible(driver, EXPORT_OPTION_PDF).click()

    def assert_a_file_was_downloaded(self, driver) -> None:
        """Assert a COMPLETE file lands in the capture dir after the export.

        Today ExportControl awaits the resolved Blob and discards it (ExportControl.tsx:78) — no
        object URL, no anchor click — so no bytes ever reach the browser and the capture dir stays
        empty: this poll exhausts the timeout and the assertion fails. green-frontend delivers the
        blob as a download and a real, non-empty, fully-written file appears.

        Strict, not "dir non-empty": the file must exist, be fully written (no `.crdownload`
        partial), carry a non-zero size, and be a `.pdf` (the exported format) — a truncated,
        still-streaming, or wrong-format download must not pass.
        """
        downloaded = self._wait_for_completed_download(driver)
        assert downloaded is not None, (
            "expected a file to be downloaded to the browser after a successful PDF export, but no "
            f"complete file appeared in the capture dir '{self._download_dir}' within "
            f"{WAIT_TIMEOUT_SECONDS}s (ExportControl resolves the blob but never delivers it as a "
            "download)"
        )
        size = os.path.getsize(downloaded)
        assert size > 0, (
            f"expected the downloaded export file '{downloaded}' to have content, but it was empty "
            f"({size} bytes)"
        )
        name = os.path.basename(downloaded)
        assert name.lower().endswith(_EXPORTED_PDF_SUFFIX), (
            f"expected the PDF export to deliver a '{_EXPORTED_PDF_SUFFIX}' file to the browser, but "
            f"the downloaded file was named '{name}'"
        )

    def _wait_for_completed_download(self, driver) -> str | None:
        """Poll the capture dir until a fully-written (non-`.crdownload`) file appears; else None."""
        deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            completed = self._completed_download_path()
            if completed is not None:
                return completed
            time.sleep(_POLL_INTERVAL_SECONDS)
        return self._completed_download_path()

    def _completed_download_path(self) -> str | None:
        for name in os.listdir(self._download_dir):
            if name.endswith(_PARTIAL_DOWNLOAD_SUFFIX):
                continue
            path = os.path.join(self._download_dir, name)
            if os.path.isfile(path):
                return path
        return None
