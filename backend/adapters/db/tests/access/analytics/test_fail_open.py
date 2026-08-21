"""The envelope every analytics write shares, tested where the write is not.

Its three promises are the ones a caller of an analytics adapter depends on and
can never observe: the session is closed whatever happens, a database failure
becomes the fallback value instead of an exception, and a bug in this package is
NOT swallowed. Each is checked here rather than four times over in the adapters,
which is the point of naming the envelope at all.
"""

import pytest
from sqlalchemy.exc import OperationalError

from access.analytics.fail_open import in_own_session


class _RecordingSession:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _factory(session):
    return lambda: session


class TestTheWorkSucceeds:
    async def test_should_answer_with_the_works_result_and_close_the_session(self):
        session = _RecordingSession()

        async def work(handed) -> str:
            assert handed is session, "the work runs on the session the factory built"
            return "written"

        result = await in_own_session(_factory(session), "nothing failed", work, "fallback")

        assert result == "written", f"expected the work's own answer, got {result!r}"
        assert session.closed, "the session must be closed on the success path too"


class TestTheDatabaseFails:
    @pytest.mark.parametrize(
        "failure",
        [
            OperationalError("INSERT", {}, Exception("connection refused")),
            OSError("socket went away"),
            TimeoutError(),
        ],
        ids=["driver", "socket", "deadline"],
    )
    async def test_should_answer_with_the_fallback_and_still_close(self, failure):
        session = _RecordingSession()

        async def work(_) -> str:
            raise failure

        result = await in_own_session(_factory(session), "the write failed", work, "fallback")

        assert result == "fallback", (
            f"an infrastructure failure must answer with the fallback, got {result!r}"
        )
        assert session.closed, "the session must be closed after a failure"


class TestThePackageItselfIsBroken:
    async def test_should_let_a_programming_error_out_rather_than_report_a_database_fault(self):
        session = _RecordingSession()

        async def work(_) -> str:
            raise AttributeError("model has no such column")

        with pytest.raises(AttributeError):
            await in_own_session(_factory(session), "the write failed", work, "fallback")

        assert session.closed, "the session must be closed even when the error travels out"
