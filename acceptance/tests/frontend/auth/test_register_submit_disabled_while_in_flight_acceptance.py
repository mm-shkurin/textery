from tests.frontend.abstract_frontend_test import AbstractFrontendTest


class TestRegisterSubmitDisabledWhileInFlightAcceptance(AbstractFrontendTest):
    """UI Test Scenario 2.3: In-flight submit buttons are disabled to prevent
    duplicate submission.

    Given the user has filled the registration form and clicked submit
    When the request is still in flight
    Then the submit button is disabled
    And a second click does not trigger a second request
    """

    def test_should_disable_submit_button_immediately_after_click(
        self, webdriver, app_url, register_page_statements
    ):
        register_page_statements.navigate_to_register_page(webdriver, app_url)
        register_page_statements.fill_registration_form(
            webdriver, "newuser@example.ru", "Password1!", "Password1!"
        )

        register_page_statements.click_submit_button(webdriver)

        register_page_statements.assert_submit_button_is_disabled(webdriver)

        register_page_statements.click_submit_button_ignoring_disabled_state(webdriver)

        register_page_statements.assert_no_duplicate_registration_request(webdriver)
