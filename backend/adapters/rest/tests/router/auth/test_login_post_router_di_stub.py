import pytest

# Imported directly, not via pytest.importorskip: this test IS the composition-root
# guard -- it must fail loudly if router.auth.auth_router stops importing, not skip
# and let the suite report green.
from router.auth import auth_router as auth_router_module

get_login_user_usecase = auth_router_module.get_login_user_usecase
get_refresh_access_token_usecase = auth_router_module.get_refresh_access_token_usecase


class TestLoginAndRefreshDependencyStubs:
    """Coverage: the /login and /refresh DI stubs raise NotImplementedError.

    Given the provider is invoked directly rather than overridden by the composition root
    When it is called
    Then it raises NotImplementedError

    The stub is what makes an unwired route fail loudly instead of silently
    defaulting to some usecase nobody chose. Scenario 3.1's STOP turned on exactly
    this property, so it is pinned rather than left as an untested `raise`.
    """

    @pytest.mark.parametrize(
        "provider",
        [get_login_user_usecase, get_refresh_access_token_usecase],
        ids=["login", "refresh"],
    )
    def test_should_raise_not_implemented_error(self, provider):
        with pytest.raises(NotImplementedError) as excinfo:
            provider()

        assert str(excinfo.value) == "wired by the application composition root", (
            f"unexpected NotImplementedError message: {excinfo.value}"
        )
