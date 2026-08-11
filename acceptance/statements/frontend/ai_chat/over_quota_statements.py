"""Statements for UI scenario 0.2 — the over-quota editor: no instruction can be typed.

**Contract gap:** nothing tells the client, on document open, that the account is out of
quota. **Green owes a quota-state read the editor route can issue on open**, carrying the
exhausted flag and the same `resets_at` instant the 429 body carries. `over_quota_session.py`'s
docstring states the gap in full and shows how the Given is reached over HTTP.

Sign-in, the click-through into the editor route and the chat-panel element resolver live in
`editor_route_statements.py` — shared with scenario 1.1, which needs the same three steps.
The navigation rationale for this scenario (the document exists and belongs to the signed-in
user, so its row is CLICKED) is recorded there.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from statements.frontend.ai_chat.editor_route_statements import (
    MESSAGE_INPUT,
    SEND_BUTTON,
    EditorRouteStatements,
)
from statements.frontend.ai_chat.over_quota_session import (
    OverQuotaAccount,
    issue_account_over_its_daily_quota,
)

# Named by THIS test and existing nowhere else when it was written. Presence assertions use
# exact testids on purpose — a `[data-testid^='ai-chat']` prefix would be satisfied by any
# incidental wrapper, which is the mirror of why 0.1's *absence* check needed the prefix.
QUOTA_RESET_HINT = (By.CSS_SELECTOR, "[data-testid='ai-chat-quota-reset-hint']")
REVISIONS_TOGGLE = (By.CSS_SELECTOR, "[data-testid='ai-chat-revisions-toggle']")
REVISIONS_PANEL = (By.CSS_SELECTOR, "[data-testid='ai-chat-revisions-panel']")

# THIS TEST SPLITS THE HINT INTO TWO ELEMENTS, and the split is the point. The sentence in
# mockups/desktop/06-over-quota.html ends in a wall-clock countdown ("через 6 ч 12 мин") no
# literal can pin — a reason to give the invariant half its own element, not to weaken the
# assertion to a prefix match. Green renders the lead here and the countdown in a sibling.
QUOTA_RESET_HINT_LEAD = (By.CSS_SELECTOR, "[data-testid='ai-chat-quota-reset-hint-lead']")
EXPECTED_RESET_HINT_LEAD = "Дневной лимит правок исчерпан"

# Required of the hint element because it is what makes the assertion strict: the rendered
# copy is a localized countdown, the attribute is the `resets_at` the API itself returned.
# A hint whose prose says one thing while the contract says another fails here.
RESETS_AT_ATTRIBUTE = "data-resets-at"

# The revisions panel is "backed by GET /revisions" (02_UI_Tests.md, DSL Technical Reference),
# so "remains usable" means it lists history — an empty container would satisfy a
# presence-only check while the read behind it is broken. Revision 1 is the one row that can
# be named by a literal: `endpoints.md` guarantees a document's first mutation writes a
# BASELINE revision 1 holding the pre-mutation content, and the setup completes at least one
# edit. The total count is deliberately not asserted — it tracks the env-configured quota, and
# deriving it would be the test computing its own expected value.
BASELINE_REVISION_ROW = (
    By.CSS_SELECTOR, "[data-testid='ai-chat-revision-row'][data-revision-number='1']"
)


class OverQuotaStatements(EditorRouteStatements):
    def open_a_document_of_an_account_over_its_quota(
        self, driver: WebDriver, app_url: str
    ) -> OverQuotaAccount:
        """Put a fresh account over quota, sign it in, and CLICK its document open.

        A live session, not a seeded one: the editor route loads the document over the API on
        mount and a fake token 401s there, collapsing the client to the landing.
        """
        account = issue_account_over_its_daily_quota()
        self._sign_in_as(driver, app_url, account)
        self._open_the_only_document_by_clicking_it(driver, app_url, account)
        return account

    def assert_the_chat_input_is_disabled(self, driver: WebDriver) -> None:
        """Both halves of "cannot type an instruction".

        The send control is asserted beside the input because a disabled input next to a
        live send control still submits — whatever the composer already holds, or an empty
        instruction — and the scenario would pass while the user is not actually stopped.
        """
        message_input = self._chat_panel_descendant(driver, MESSAGE_INPUT, "message input")
        assert not message_input.is_enabled(), "expected the chat message input to be disabled"

        send_button = self._chat_panel_descendant(driver, SEND_BUTTON, "send control")
        assert not send_button.is_enabled(), "expected the chat send control to be disabled"

    def assert_the_reset_hint_is_shown(self, driver: WebDriver, expected_resets_at: str) -> None:
        hint = self._chat_panel_descendant(driver, QUOTA_RESET_HINT, "quota reset hint")
        assert hint.is_displayed(), "expected the quota reset hint to be displayed"

        actual_resets_at = hint.get_attribute(RESETS_AT_ATTRIBUTE) or ""
        assert actual_resets_at == expected_resets_at, (
            f"expected the reset hint's {RESETS_AT_ATTRIBUTE} to be the instant the API "
            f"refused with ('{expected_resets_at}'), got '{actual_resets_at}'"
        )

        lead = self._chat_panel_descendant(driver, QUOTA_RESET_HINT_LEAD, "reset hint lead")
        actual_lead = lead.text.strip()
        assert actual_lead == EXPECTED_RESET_HINT_LEAD, (
            f"expected the reset hint lead to be '{EXPECTED_RESET_HINT_LEAD}', "
            f"got '{actual_lead}'"
        )

    def open_the_revisions_panel(self, driver: WebDriver) -> None:
        """The action half of "the revisions panel remains usable".

        Split out of the assertion because it CLICKS: an `assert*` method that mutates page
        state leaves the scenario reading as three pure checks while the third silently opens
        a panel that anything added after it would inherit.

        The toggle's enabled state is asserted before the click, since the regression this
        spec line forbids is precisely an over-quota branch that disables the revisions
        control along with the composer.
        """
        toggle = self._chat_panel_descendant(driver, REVISIONS_TOGGLE, "revisions control")
        assert toggle.is_displayed(), "expected the revisions control to stay displayed"
        assert toggle.is_enabled(), "expected the revisions control to stay enabled over quota"
        toggle.click()

    def assert_the_revisions_panel_lists_the_history(self, driver: WebDriver) -> None:
        """Usable means it LISTS revisions, not merely that a container appeared.

        A container-only check would pass a panel whose `GET /revisions` read the over-quota
        branch broke or short-circuited — it would render empty and still be "displayed".
        """
        panel = self._chat_panel_descendant(driver, REVISIONS_PANEL, "revisions panel")
        assert panel.is_displayed(), "expected the revisions panel to open"

        baseline_rows = panel.find_elements(*BASELINE_REVISION_ROW)
        assert len(baseline_rows) == 1, (
            "expected the revisions panel to list exactly one baseline revision 1 (written "
            f"by the first mutation the setup completed), found {len(baseline_rows)}"
        )
