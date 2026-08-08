"""Selenium DSL for story 10, UI scenario 1.1 — pagination waits for the document font.

Given a document is opened and the document font has not finished loading
When the editor is displayed
Then the measuring state is shown
And no page count is displayed
And the state is visibly distinct from an error and from an empty document
"""

from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.base_frontend_statements import BaseFrontendStatements
from statements.frontend.editor.document_font_hold import DocumentFontHoldMixin
from statements.frontend.editor.live_document_setup import SeededDocument
from statements.frontend.editor.pagination_measuring_locators import (
    EMPTY_DOCUMENT_HINT,
    EXPECTED_MEASURING_BUSY,
    EXPECTED_MEASURING_MESSAGE,
    EXPECTED_MEASURING_STATUS,
    EXPECTED_RAIL_SKELETON_COUNT,
    EXPECTED_SPINNER_ROLE,
    MEASURING_MESSAGE,
    MEASURING_SPINNER,
    MEASURING_SURFACE,
    PAGE_COUNT,
    PAGE_RAIL_SKELETON,
    PAGINATION_ERROR,
    PAGINATION_STATUS,
    SHEET_SKELETON,
)
from statements.frontend.editor.seeded_document_navigation import SeededDocumentNavigationMixin
from statements.frontend.generation.manual_editor_statements import MANUAL_EDITOR


class PaginationMeasuringStatements(
    DocumentFontHoldMixin, SeededDocumentNavigationMixin, BaseFrontendStatements
):
    """Open a saved document with the font held mid-load, then read the pre-layout state."""

    def given_the_document_is_open_with_the_font_still_loading(
        self, driver: WebDriver, app_url: str, document: SeededDocument
    ) -> None:
        """The scenario's whole Given, in the one order that can produce it.

        The hold is installed BEFORE any navigation because it runs at document start and the app
        reads font readiness during its own boot — install it after `_establish_logged_in_
        precondition`'s navigation and the editor has already decided the font is ready. That
        ordering is an infrastructure invariant, so it lives here rather than as a comment in the
        test class, where nothing enforces it.
        """
        self.hold_the_document_font_mid_load(driver)
        self.open_the_seeded_document_in_the_editor(driver, app_url, document)

    def assert_the_measuring_state_is_shown(self, driver: WebDriver) -> None:
        """The editor is up and showing the measuring state: skeleton sheet + rail skeletons.

        The editor shell is waited for FIRST so a failure can tell the two apart: an editor that
        never opened is a broken Given, and an editor that opened straight into laid-out sheets is
        the defect this scenario exists to catch. Without the shell wait both report as
        "pagination-measuring never appeared".

        Each part is asserted individually rather than implied by the surface, because the DSL
        Technical Reference defines the measuring state as exactly "Skeleton sheet + rail
        skeletons, no page count in the status bar". A surface that renders the wording with no
        skeleton sheet is a static notice occupying the content area, not a measuring state.
        """
        self._wait_for_visible(
            driver,
            MANUAL_EDITOR,
            f"expected opening a document to display the editor, but {MANUAL_EDITOR[1]} never "
            "appeared — the scenario's Given did not hold and nothing below it means anything",
        )
        self._wait_for_visible(
            driver,
            MEASURING_SURFACE,
            "expected the editor to show the measuring state while the document font is still "
            f"loading, but {MEASURING_SURFACE[1]} never appeared",
        )
        self._assert_element_text_equals(
            driver, MEASURING_MESSAGE, EXPECTED_MEASURING_MESSAGE, "the measuring message"
        )
        self._assert_the_measuring_surface_announces_itself_busy(driver)
        self._assert_the_skeletons_stand_in_for_the_unlaid_pages(driver)

    def _assert_the_measuring_surface_announces_itself_busy(self, driver: WebDriver) -> None:
        """The spinner is a LIVE indicator, not an element with a spinner's testid.

        Visibility alone is satisfied by an empty div, which is how a static notice passes for a
        measuring state. The role and busy flag are also what make this state distinct to a screen
        reader, where "visibly distinct" has no meaning and the error and empty states are told
        apart by what they announce.
        """
        spinner = self._wait_for_visible(
            driver,
            MEASURING_SPINNER,
            f"expected a live progress indicator while measuring, but {MEASURING_SPINNER[1]} "
            "never appeared — a message with no indicator is a static notice",
        )
        actual_role = spinner.get_attribute("role")
        assert actual_role == EXPECTED_SPINNER_ROLE, (
            f"expected the measuring spinner to announce role='{EXPECTED_SPINNER_ROLE}', got "
            f"'{actual_role}' — the state is not distinguishable to a screen reader"
        )
        surface = driver.find_element(*MEASURING_SURFACE)
        actual_busy = surface.get_attribute("aria-busy")
        assert actual_busy == EXPECTED_MEASURING_BUSY, (
            f"expected the measuring surface to carry aria-busy='{EXPECTED_MEASURING_BUSY}', got "
            f"'{actual_busy}' — assistive tech is told the editor has settled while it measures"
        )

    def _assert_the_skeletons_stand_in_for_the_unlaid_pages(self, driver: WebDriver) -> None:
        """A skeleton SHEET in the content area and exactly the rail's placeholder rows.

        The sheet skeleton is the element neither state this must be distinct from renders: the
        error state shows an error surface, and the empty document shows a real, blank sheet.
        """
        self._wait_for_visible(
            driver,
            SHEET_SKELETON,
            f"expected a skeleton sheet in the content area while measuring, but "
            f"{SHEET_SKELETON[1]} never appeared — the DSL defines the measuring state as a "
            "skeleton sheet plus rail skeletons, and this half of it is missing",
        )
        self._wait_for_visible(
            driver,
            PAGE_RAIL_SKELETON,
            f"expected the page rail to show placeholder rows while measuring, but "
            f"{PAGE_RAIL_SKELETON[1]} never appeared — the rail rendered nothing",
        )
        self._assert_visible_element_count(
            driver,
            PAGE_RAIL_SKELETON,
            EXPECTED_RAIL_SKELETON_COUNT,
            "page-rail skeleton row(s) while measuring",
        )

    def assert_no_page_count_is_displayed_and_the_status_reads_measuring(
        self, driver: WebDriver
    ) -> None:
        """No count, anywhere — a count here would have been computed on substituted metrics.

        Absence AND the status bar's wording, because the two failures are different. A missing
        `page-count` node with a status bar already reading "Страница 1 из 1" would satisfy a pure
        absence check while telling the user a page count in prose.
        """
        self._assert_stays_not_visible(
            driver,
            PAGE_COUNT,
            f"expected NO page count while the document font is still loading, but "
            f"{PAGE_COUNT[1]} is shown — a count laid out on substituted font metrics would "
            "change under the user the moment the real font arrived",
        )
        self._assert_element_text_equals(
            driver, PAGINATION_STATUS, EXPECTED_MEASURING_STATUS, "the pagination status"
        )

    def assert_measuring_is_distinct_from_error_and_empty_document(
        self, driver: WebDriver
    ) -> None:
        """Both halves of "visibly distinct": the skeleton sheet is up, and neither rival is.

        The positive half is asserted HERE rather than borrowed from the assertions above, because
        absence checks alone are also satisfied by an editor rendering nothing at all. The skeleton
        sheet is the fact that separates all three states: measuring shows a placeholder sheet,
        1.3's error state shows `pagination-error`, and 2.3's empty document shows a real blank
        sheet with `empty-document-hint`.

        The two rivals are then ruled out explicitly rather than assumed from the measuring surface
        being up, because an implementation that renders the empty-document sheet UNDERNEATH a
        measuring overlay satisfies every positive assertion while showing the user a blank page
        and a spinner at once — and an error surface left standing under it tells them the document
        failed and is loading simultaneously.
        """
        self._wait_for_visible(
            driver,
            SHEET_SKELETON,
            "expected the measuring state to be positively identifiable by its skeleton sheet, "
            f"but {SHEET_SKELETON[1]} is not shown — absence of the other two states is not, on "
            "its own, evidence that THIS state is the one on screen",
        )
        self._assert_stays_not_visible(
            driver,
            PAGINATION_ERROR,
            f"expected the measuring state to be distinct from an error, but {PAGINATION_ERROR[1]}"
            " is shown alongside it — the user is told the document failed and is loading at once",
        )
        self._assert_stays_not_visible(
            driver,
            EMPTY_DOCUMENT_HINT,
            "expected the measuring state to be distinct from an empty document, but "
            f"{EMPTY_DOCUMENT_HINT[1]} is shown — a document that has not been laid out yet is "
            "being presented as one that has no content",
        )
