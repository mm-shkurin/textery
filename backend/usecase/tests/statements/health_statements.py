"""Test doubles for the `HealthProbe` port.

Hand-written rather than `mocker.Mock`: the port's whole contract is "returns or
raises", and a class that does exactly that reads as the condition under test
instead of as mock configuration.
"""


class _ReachableProbe:
    async def ping(self) -> None:
        return None


class _FailingProbe:
    def __init__(self, error: BaseException) -> None:
        self._error = error

    async def ping(self) -> None:
        raise self._error


def a_reachable_probe() -> _ReachableProbe:
    return _ReachableProbe()


def a_failing_probe() -> _FailingProbe:
    return _FailingProbe(OSError("connection refused"))


def a_probe_failing_with(error: BaseException) -> _FailingProbe:
    return _FailingProbe(error)
