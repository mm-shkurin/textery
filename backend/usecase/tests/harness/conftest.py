"""Fixtures for the harness gates -- tests whose subject is the test runner itself."""

import pytest

from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements


@pytest.fixture
def forgotten_await_gate_statements():
    return ForgottenAwaitGateStatements()
