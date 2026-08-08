"""What the measuring surface must actually BE, beyond a visible element with the right testid.

Split out of `pagination_measuring_statements.py` to keep it under the 200-line cap, along the
same seam `document_font_hold.py` and `seeded_document_navigation.py` were split on: that module
sequences the scenario's Given/Then, this one holds the composition of the measuring state itself.

The two assertions here are the ones that stop a static notice from passing for a measuring
state. Scenarios 1.2 and 1.3 read the same surface — 1.3 for the moment it is REPLACED by the
error state — so they need this vocabulary without inheriting 1.1's Thens.
"""

from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.editor.pagination_measuring_locators import (
    EXPECTED_MEASURING_BUSY,
    EXPECTED_RAIL_SKELETON_COUNT,
    EXPECTED_SPINNER_ROLE,
    MEASURING_SPINNER,
    MEASURING_SURFACE,
    PAGE_RAIL_SKELETON,
    SHEET_SKELETON,
)


class MeasuringSurfaceAssertionsMixin:
    """Assert the measuring surface announces itself and renders its placeholders."""

    def _assert_the_measuring_surface_announces_itself_busy(self, driver: WebDriver) -> None:
        """The spinner is a LIVE indicator, not an element with a spinner's testid.

        Visibility alone is satisfied by an empty div, which is how a static notice passes for a
        measuring state. The role and busy flag are also what make this state distinct to a screen
        reader, where "visibly distinct" has no meaning and the error and empty states are told
        apart by what they announce.
        """
        self._wait_for_visible(
            driver,
            MEASURING_SPINNER,
            f"expected a live progress indicator while measuring, but {MEASURING_SPINNER[1]} "
            "never appeared — a message with no indicator is a static notice",
        )
        self._assert_element_attribute_equals(
            driver,
            MEASURING_SPINNER,
            "role",
            EXPECTED_SPINNER_ROLE,
            "the measuring spinner",
            "the state is not distinguishable to a screen reader",
        )
        self._assert_element_attribute_equals(
            driver,
            MEASURING_SURFACE,
            "aria-busy",
            EXPECTED_MEASURING_BUSY,
            "the measuring surface",
            "assistive tech is told the editor has settled while it measures",
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
