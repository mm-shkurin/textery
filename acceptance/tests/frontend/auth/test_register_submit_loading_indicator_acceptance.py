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
    which response is on its way back — a fresh 201 and a duplicate-email
    rejection produce the same observable window. That is what Scenario 3.1
    specifies, not an oversight: the indicator's job is to say "waiting",
    and it has the same job either way.
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
