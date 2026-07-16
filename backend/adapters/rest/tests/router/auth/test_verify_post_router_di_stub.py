import pytest

auth_router_module = pytest.importorskip(
    "router.auth.auth_router",
    reason="RED: router.auth.auth_router module does not exist (ModuleNotFoundError)",
)
get_verify_account_usecase = auth_router_module.get_verify_account_usecase


class TestGetVerifyAccountUsecaseDependencyStub:
    """Coverage: get_verify_account_usecase DI stub raises NotImplementedError.

    Given real usecase wiring has not landed yet
    When the DI provider function is invoked directly (not overridden)
    Then it raises NotImplementedError
    """

    def test_should_raise_not_implemented_error(self):
        with pytest.raises(NotImplementedError) as excinfo:
            get_verify_account_usecase()

        assert str(excinfo.value) == "wired by the application composition root", (
            f"unexpected NotImplementedError message: {excinfo.value}"
        )
