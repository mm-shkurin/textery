"""Fixtures for the child-scope guards, §1.2 (edits) and §1.3 (revisions).

The three log-collecting fixtures yield rather than return: `RecordingLogger`
attaches a handler and forces the level on a process-global logger, so a test that
fails mid-assertion must still put both back.
"""

import pytest

from statements.ai_edit_refusal_log_statements import AiEditRefusalLogStatements
from statements.ai_edit_scope_guard_statements import AiEditScopeGuardStatements
from statements.ai_edit_store_failure_statements import AiEditStoreFailureStatements
from statements.refusal_record_shape_statements import RefusalRecordShapeStatements
from statements.revision_number_range_statements import RevisionNumberRangeStatements
from statements.revision_range_refusal_log_statements import RevisionRangeRefusalLogStatements
from statements.revision_outage_statements import RevisionOutageStatements
from statements.revision_refusal_log_statements import RevisionRefusalLogStatements
from statements.revision_scope_guard_statements import RevisionScopeGuardStatements
from statements.revision_silence_statements import RevisionSilenceStatements


@pytest.fixture
def ai_edit_scope_guard_statements():
    return AiEditScopeGuardStatements()


@pytest.fixture
def ai_edit_store_failure_statements():
    return AiEditStoreFailureStatements()


@pytest.fixture
def ai_edit_refusal_log_statements():
    statements = AiEditRefusalLogStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def revision_scope_guard_statements():
    return RevisionScopeGuardStatements()


@pytest.fixture
def revision_number_range_statements():
    return RevisionNumberRangeStatements()


@pytest.fixture
def revision_outage_statements():
    return RevisionOutageStatements()


@pytest.fixture
def revision_refusal_log_statements():
    statements = RevisionRefusalLogStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def revision_range_refusal_log_statements():
    statements = RevisionRangeRefusalLogStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def revision_silence_statements():
    statements = RevisionSilenceStatements()
    yield statements
    statements.stop_collecting()


@pytest.fixture
def refusal_record_shape_statements(
    ai_edit_refusal_log_statements, revision_refusal_log_statements
):
    return RefusalRecordShapeStatements(
        ai_edit_refusal_log_statements, revision_refusal_log_statements
    )
