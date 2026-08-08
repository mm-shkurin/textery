import pytest

from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# RED, verified live against the full stack (backend + Postgres + nginx-served frontend build)
# on 2026-08-08 — not an analytical prediction.
#
# OBSERVED FAILURE: selenium.common.exceptions.TimeoutException — "expected the editor to show
# the measuring state while the document font is still loading, but [data-testid='manual-editor']
# [data-testid='pagination-measuring'] never appeared".
#
# WHAT THAT MEANS, and the ordering of the assertions is what makes it readable: the editor
# shell DID mount (the wait on `[data-testid='manual-editor']` passed, so the history-open path
# works and the Given is real), and `assert_the_document_font_has_not_finished_loading` passed
# too — `document.fonts.ready` was observed still pending on the page under test. So the run
# reached the scenario's actual subject and found it missing. There is no pre-layout state in
# the product at all: `grep -rn "pagination-measuring\|page-rail-skeleton\|pagination-status\|
# empty-document-hint\|pagination-error" frontend/src` returns nothing. The editor renders its
# content area immediately, with no notion of font readiness anywhere in the tree.
#
# OWED BY GREEN (align-design paints them; green-frontend decides when each is shown):
# `pagination-measuring`, carrying `aria-busy='true'`, with `pagination-measuring-message` reading
# "Готовим страницы…" and a `pagination-measuring-spinner` carrying `role='status'`;
# `page-sheet-skeleton` in the content area and exactly three `page-rail-skeleton` rows in the
# rail (the mockup's count — `mockups/desktop/02-measuring.html`); and a `pagination-status`
# reading "Расчёт страниц…" with NO `page-count` node while the font is unresolved.
# `pagination-error` (1.3) and `empty-document-hint` (2.3) must not be shown at the same time;
# they are asserted absent here and are those scenarios' to render.
#
# `page-sheet-skeleton` is the load-bearing one for the third Then. The DSL Technical Reference
# defines the measuring state as "Skeleton sheet + rail skeletons", and the skeleton sheet is the
# only element that positively separates all three states — 1.3's error shows an error surface and
# 2.3's empty document shows a real blank sheet. Two absence checks alone would also pass on an
# editor that rendered nothing at all, which is why "visibly distinct" needs a positive anchor.
@pytest.mark.skip(
    reason="RED: TimeoutException — [data-testid='pagination-measuring'] never appeared; "
    "the editor has no pre-layout measuring state yet (see the recorded observation above)"
)
class TestPaginationMeasuringStateAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.1: Pagination waits for the document font.

    Given a document is opened and the document font has not finished loading
    When the editor is displayed
    Then the measuring state is shown
    And no page count is displayed
    And the state is visibly distinct from an error and from an empty document

    Why the font is HELD rather than blocked or throttled. The three pre-layout scenarios
    (1.1 still loading, 1.2 resolved, 1.3 never loads) are three different states of the same
    resource, and the only failure mode that matters here is telling them apart. A URL block —
    the lever this suite already uses for the export GET — makes `document.fonts.ready` RESOLVE
    with a substituted face, which is 1.3's Given wearing 1.1's clothes; the spec-phase summary
    records the same trap from the export side (an unresolvable face does not error, it
    substitutes and succeeds, so "it rendered" is never evidence the right font was used). The
    hold in `document_font_hold.py` leaves `ready` permanently pending, and
    `assert_the_document_font_has_not_finished_loading` reads that back off the page so the
    Given is an observation rather than an assumption.

    The document is seeded over HTTP and then opened by CLICKING (Мои работы, then the row) —
    the only route to the editor the product has today, since story 18 put the create path on
    `mode='auto'` and left `openDocumentFromHistory` as the sole branch that mounts the editor
    for an existing document. It is also deliberately NOT an empty document: the empty state is
    one of the two states 1.1 must be distinguishable from.
    """

    def test_should_show_the_measuring_state_and_no_page_count_while_the_font_loads(
        self, webdriver, app_url, editor_document_statements, pagination_measuring_statements
    ):
        document = editor_document_statements.given_a_saved_document()

        pagination_measuring_statements.given_the_document_is_open_with_the_font_still_loading(
            webdriver, app_url, document
        )

        pagination_measuring_statements.assert_the_document_font_has_not_finished_loading(webdriver)
        pagination_measuring_statements.assert_the_measuring_state_is_shown(webdriver)
        pagination_measuring_statements.assert_no_page_count_is_displayed_and_the_status_reads_measuring(
            webdriver
        )
        pagination_measuring_statements.assert_measuring_is_distinct_from_error_and_empty_document(
            webdriver
        )
