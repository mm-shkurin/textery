import pytest

from router.generation.generation_router import (
    get_generate_document_usecase,
    get_get_generation_usecase,
    get_request_generation_usecase,
)

EXPECTED_UNWIRED_MESSAGE = "wired by the application composition root"


class TestGenerationProviderFailFast:
    """The three FastAPI dependency-provider stubs are fail-fast guards.

    In production `application/src/app/main.py` overrides all three via
    `app.dependency_overrides`. Called directly (router mounted unwired) each
    must raise NotImplementedError with the exact composition-root message,
    so a missing override surfaces immediately instead of returning a bad
    dependency.
    """

    @pytest.mark.parametrize(
        "provider",
        [
            get_request_generation_usecase,
            get_get_generation_usecase,
            get_generate_document_usecase,
        ],
        ids=["request_generation", "get_generation", "generate_document"],
    )
    def test_should_raise_not_implemented_when_called_unwired(self, provider):
        with pytest.raises(NotImplementedError) as excinfo:
            provider()

        assert str(excinfo.value) == EXPECTED_UNWIRED_MESSAGE, (
            f"expected fail-fast message '{EXPECTED_UNWIRED_MESSAGE}', "
            f"got '{excinfo.value}'"
        )
