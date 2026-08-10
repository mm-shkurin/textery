"""Fixtures for the harness gates -- tests whose subject is the test runner itself."""

import pytest

from statements.arrangement_snapshot_guard_statements import ArrangementSnapshotGuardStatements
from statements.bannerless_child_report_statements import BannerlessChildReportStatements
from statements.child_report_join_statements import ChildReportJoinStatements
from statements.disarmed_arming_probe_statements import DisarmedArmingProbeStatements
from statements.forgotten_await_gate_statements import ForgottenAwaitGateStatements
from statements.gate_reach_statements import GateReachStatements
from statements.live_harness_configuration_statements import LiveHarnessConfigurationStatements


@pytest.fixture
def forgotten_await_gate_statements():
    return ForgottenAwaitGateStatements()


@pytest.fixture
def gate_reach_statements():
    return GateReachStatements()


@pytest.fixture
def child_report_join_statements():
    return ChildReportJoinStatements()


@pytest.fixture
def bannerless_child_report_statements():
    return BannerlessChildReportStatements()


@pytest.fixture
def arrangement_snapshot_guard_statements():
    return ArrangementSnapshotGuardStatements()


@pytest.fixture
def disarmed_arming_probe_statements(monkeypatch):
    """Handed `monkeypatch` so the disarming env is restored however the test ends."""
    return DisarmedArmingProbeStatements(monkeypatch)


@pytest.fixture
def live_harness_configuration_statements(pytestconfig):
    """Handed the `config` of the run executing it -- the subject, not a fixture detail."""
    return LiveHarnessConfigurationStatements(pytestconfig)
