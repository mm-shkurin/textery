from tests.frontend.abstract_frontend_test import AbstractFrontendTest

# BLOCKED 2026-07-20 (was previously: only 3.1 skipped on a now-false contenteditable reason).
# The stale reason is gone — .me-content-area's child is a real ProseMirror contenteditable
# div (data-testid="editor-content-area"), so the Statements now type into it correctly (locator
# fixed in manual_editor_statements.py this commit). But un-skipping exposed the true, larger
# blocker: Story 7 (authorization) gated the type -> mode -> editor flow behind a live session
# (useFlowNavigation.startFlow: unauthenticated -> /register). The editor is unreachable without
# a backend-issued JWT the API accepts. Seeding a fake sessionStorage token does NOT work: the
# editor's mount calls createDocument, the 401 triggers refresh, refresh fails -> clearSession ->
# DocumentGenerationFlow collapses to the landing (verified live against the frontend dev server).
# So ALL three scenarios (1.2 / 2.1 / 3.1), not just 3.1, need a real authenticated session =
# live backend + Postgres. That stack is the backend session's ownership and is infra-guardrailed
# on this shared host, so it cannot be stood up here. Un-skip + green once a full stack with real
# register -> verify -> login is available (frontend nav must authenticate first, not just click
# the CTA). This skip is now TRUE and dated, replacing the dangerous stale-false one.
# UNBLOCKED 2026-07-22: the full stack IS available (backend :8100 + Postgres + Redis, all
# healthy). The register -> verify -> login -> POST /api/v1/documents round trip was driven
# live and returns 201, so the blocker recorded above no longer holds.


class TestManualEditorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 1.2: Selecting Ручной режим opens the empty editor.

    Given the mode modal is open
    When the visitor selects "Ручной режим"
    Then the mode modal closes
    And an empty editor opens, scoped to the chosen document type
    """

    def test_should_open_manual_editor_scoped_to_document_type(
        self, webdriver, app_url, manual_editor_statements
    ):
        manual_editor_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_statements.assert_mode_modal_is_closed(webdriver)
        manual_editor_statements.assert_manual_editor_is_open_for_doklad(webdriver)


class TestManualEditorEmptyStateAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.1: A freshly created document shows an empty, ready-to-type editor.

    Given a visitor has just created a manual document
    Then the editor shows an empty content area with a placeholder, not a loading skeleton
    And the formatting toolbar is visible with heading, paragraph, list, bold, and italic
      controls
    And the breadcrumb shows the chosen document type and "Ручной режим"
    """

    # FIXED + UN-SKIPPED 2026-07-23. The 2026-07-22 defect (placeholder rendered nowhere on the
    # inline-only schema) is resolved: InlinePlaceholder (frontend/src/.../inlinePlaceholder.ts)
    # decorates the empty ProseMirror root with data-placeholder + is-editor-empty, and
    # ManualEditor.css paints the text via `.ProseMirror.is-editor-empty::before`. The Statement's
    # `.me-placeholder` locator was repointed at that real mechanism (data-placeholder attr +
    # is-editor-empty class + ::before computed content) — the ::before paint is the coverage the
    # jsdom placeholder unit tests explicitly owed to selenium.
    def test_should_show_empty_editor_with_placeholder_and_toolbar(
        self, webdriver, app_url, manual_editor_statements
    ):
        manual_editor_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_statements.assert_no_loading_skeleton_is_shown(webdriver)
        manual_editor_statements.assert_content_placeholder_is_visible(webdriver)
        manual_editor_statements.assert_toolbar_controls_are_visible(webdriver)
        manual_editor_statements.assert_manual_editor_is_open_for_doklad(webdriver)


class TestManualEditorBoldFormattingAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.1: Applying a format changes the content and highlights the
    active toolbar button.

    Given the visitor has typed some text in the editor
    When the visitor selects the text and applies bold formatting
    Then the selected text is rendered bold
    And the bold toolbar button shows as active while the cursor remains inside it
    """

    def test_should_render_selected_text_bold_and_activate_bold_button(
        self, webdriver, app_url, manual_editor_statements
    ):
        manual_editor_statements.open_manual_editor_for_doklad(webdriver, app_url)

        manual_editor_statements.type_text_in_editor(webdriver, "Test heading text")
        manual_editor_statements.select_all_text_in_editor(webdriver)
        manual_editor_statements.apply_bold_formatting(webdriver)

        manual_editor_statements.assert_selected_text_is_bold(webdriver, "Test heading text")
        manual_editor_statements.assert_bold_button_is_active(webdriver)
