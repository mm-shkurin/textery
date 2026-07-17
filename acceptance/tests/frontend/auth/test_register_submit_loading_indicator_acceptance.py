from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterSubmitLoadingIndicatorAcceptance(AbstractFrontendTest):
    """UI Test Scenario 3.1: Registration submission shows a loading state.

    Given the user has filled the registration form with valid data
    When the user submits the form
    Then a loading indicator is shown until the response arrives

    The in-flight window is a REAL `POST /api/v1/auth/register` round-trip
    (Scenario 5.1 replaced the useSubmitPlaceholder 500ms crutch with the
    live call), and it is wide enough for Selenium to catch the indicator
    before the response settles.

    The assertion inspects only the in-flight state, so it does not care
    which response is on its way back. That is what Scenario 3.1 specifies,
    not an oversight: the indicator's job is to say "waiting", and it has
    the same job either way.

    That insensitivity is only SAFE because both paths are wide enough to
    observe, which is a timing claim and so was measured rather than
    assumed (2026-07-17): a fresh 201 takes ~0.96s, a duplicate-email 409
    ~0.77-1.04s. The email below is hardcoded, so the first run ever to
    reach a clean database takes the 201 path and every run after it takes
    the 409 — both were exercised green here. Contrast the ~5ms 404 this
    test was skipped for: two orders of magnitude narrower, and genuinely
    unobservable. If the backend ever short-circuits the duplicate check
    before its expensive work, that margin is what disappears first.
    """

    def test_should_show_loading_indicator_while_submission_is_in_flight(
        self, webdriver, app_url, register_page_statements
    ):
        register_page_statements.navigate_to_register_page(webdriver, app_url)
        register_page_statements.fill_registration_form(
            webdriver, "newuser@example.ru", "Password1!", "Password1!"
        )

        register_page_statements.click_submit_button(webdriver)

        register_page_statements.assert_loading_indicator_is_visible(webdriver)
