import inspect
from uuid import uuid4

import pytest

# Imported directly, not via pytest.importorskip: this test IS the guard on the port's
# failure shape -- it must fail loudly if document_edit.ai_edit_repository stops
# importing, not skip and let the suite report green.
from document_edit.ai_edit_repository import AiEditRepository

# Port method -> the exact NotImplementedError message its body must carry. Pinned as
# literals, never read back from the module: a message compared against the module's own
# constant would widen alongside the very body it guards. The keys are the expected
# roster, so a second port method added later must fail the roster assertion rather than
# slip in with a `...` body no test ever calls.
EXPECTED_PORT_METHODS = {
    "find_scope_by_id_and_document": "AiEditRepository.find_scope_by_id_and_document",
}

# Discovered across the whole MRO, not from `vars(AiEditRepository)` alone: `vars` reads
# only the class's own `__dict__`, so a method arriving on a base Protocol -- the natural
# shape once this port is split -- would be invisible here and the roster assertion would
# pass while leaving it uncovered. `typing`/`builtins` bases contribute Protocol
# machinery, not port methods, so they are excluded.
DISCOVERED_PORT_METHODS = sorted(
    {
        name
        for klass in AiEditRepository.__mro__
        if klass.__module__ not in ("typing", "builtins")
        for name in vars(klass)
        if not name.startswith("_")
    }
)

PORT_METHOD_CASES = [pytest.param(name, id=name) for name in EXPECTED_PORT_METHODS]


class AdapterThatForgotToImplementThePort(AiEditRepository):
    """A concrete implementor that inherits every body unchanged.

    This is the shape the port's raising bodies exist to catch: an adapter written
    against `AiEditRepository` that never implemented a method. It is a real subclass,
    not a Protocol, so it is instantiable and its inherited bodies actually run.
    """


class TestAiEditRepositoryPortStub:
    """Coverage: the AiEditRepository port bodies raise instead of returning None.

    Given an adapter that inherits a port method without implementing it
    When the method is awaited
    Then it raises NotImplementedError naming the method, rather than answering
    "not found"

    A `...` body on an `async def` is a concrete coroutine returning `None`, and
    `None` is this port's "no such edit under that document" answer -- so an
    unimplemented adapter would refuse every owner their own edit, silently and with
    the canonical 404 the guard is built to emit. The raising body is the enforcement
    mechanism; every production caller goes through a real implementation or a fake,
    so nothing else ever executes it.

    The method's async shape is asserted here rather than left to `asyncio_mode =
    "auto"`: if the port body ever became a plain `def`, the raise would still fire
    inside `pytest.raises` with nothing awaited, and the silent-coroutine hazard this
    test exists to rule out would be uncovered while the test stayed green.
    """

    def test_should_expose_exactly_the_known_port_methods(self):
        assert DISCOVERED_PORT_METHODS == sorted(EXPECTED_PORT_METHODS), (
            "AiEditRepository exposes a method roster this test does not cover: "
            f"{DISCOVERED_PORT_METHODS}"
        )

    @pytest.mark.parametrize("method_name", PORT_METHOD_CASES)
    async def test_should_raise_not_implemented_error(self, method_name):
        adapter = AdapterThatForgotToImplementThePort()
        method = getattr(adapter, method_name)

        assert inspect.iscoroutinefunction(method), (
            f"AiEditRepository.{method_name} is not an async def, so awaiting it is "
            "not what this test exercised"
        )

        # Called by keyword because the port's scoping ids are keyword-only. That
        # names this method's own parameters inside a parametrized body, which is
        # deliberate: a second port method with a different signature must fail
        # here rather than be waved through, and the roster assertion above already
        # forces this test to be revisited when one arrives.
        with pytest.raises(NotImplementedError) as excinfo:
            await method(edit_id=uuid4(), document_id=uuid4())

        assert str(excinfo.value) == EXPECTED_PORT_METHODS[method_name], (
            f"unexpected NotImplementedError message from {method_name}: "
            f"{excinfo.value}"
        )
