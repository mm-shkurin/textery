import pytest

# Imported directly, not via pytest.importorskip: this test IS the composition-root
# guard -- it must fail loudly if router.document_edit.document_edit_router stops
# importing, not skip and let the suite report green.
from router.document_edit import document_edit_router as document_edit_router_module

# Provider name -> the route it feeds. Keys are the expected set, so the pairing of
# provider to id is structural rather than two parallel lists kept in sync by hand.
EXPECTED_PROVIDERS = {
    "get_queue_ai_edit_usecase": "queue-ai-edit",
    "get_stream_ai_edit_usecase": "stream-ai-edit",
    "get_get_ai_edit_usecase": "get-ai-edit",
    "get_cancel_ai_edit_usecase": "cancel-ai-edit",
    "get_list_messages_usecase": "list-messages",
    "get_list_revisions_usecase": "list-revisions",
    "get_restore_revision_usecase": "restore-revision",
}

DISCOVERED_PROVIDER_NAMES = sorted(
    name
    for name in dir(document_edit_router_module)
    if name.startswith("get_") and name.endswith("_usecase")
)

PROVIDER_CASES = [
    pytest.param(name, id=route) for name, route in EXPECTED_PROVIDERS.items()
]


class TestAiEditDependencyStubs:
    """Coverage: the seven Story 19 AI-edit DI stubs raise NotImplementedError.

    Given the provider is invoked directly rather than overridden by the composition root
    When it is called
    Then it raises NotImplementedError carrying the composition-root message

    The stub is what makes an unwired route fail loudly instead of silently binding
    some usecase nobody chose. The 37 route tests override every provider through
    `dependency_overrides`, so the stub bodies would otherwise never execute.

    The expected message is asserted as a literal rather than by importing the
    module's `_WIRED_BY_COMPOSITION_ROOT` constant: comparing the constant to itself
    would widen the test alongside the very thing it guards. For the same reason the
    provider set is discovered from the module and pinned against literal names --
    an eighth stub must fail the roster assertion, not slip through uncovered.
    """

    def test_should_expose_exactly_the_seven_known_providers(self):
        assert DISCOVERED_PROVIDER_NAMES == sorted(EXPECTED_PROVIDERS), (
            "document_edit_router exposes a provider roster this test does not cover: "
            f"{DISCOVERED_PROVIDER_NAMES}"
        )

    @pytest.mark.parametrize("provider_name", PROVIDER_CASES)
    def test_should_raise_not_implemented_error(self, provider_name):
        provider = getattr(document_edit_router_module, provider_name)

        with pytest.raises(NotImplementedError) as excinfo:
            provider()

        assert str(excinfo.value) == "wired by the application composition root", (
            f"unexpected NotImplementedError message from {provider_name}: {excinfo.value}"
        )
