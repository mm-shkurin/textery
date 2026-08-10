"""Document-export Statements fixtures (export, format, docx, filename, no-mutation).

Split out of conftest.py to keep that file under the 200-line cap. These names are
imported back into conftest (`from document_export_fixtures import ...`), so pytest
discovers them exactly as if they were defined in conftest itself. This module relies
on conftest having already inserted the acceptance dir onto sys.path before it imports
us, which makes the `statements.*` imports below resolve.
"""

import pytest_asyncio

from statements.document_export_statements import DocumentExportStatements
from statements.document_export_format_statements import DocumentExportFormatStatements
from statements.document_export_docx_statements import DocumentExportDocxStatements
from statements.document_export_filename_statements import (
    DocumentExportFilenameStatements,
)
from statements.document_export_no_mutation_statements import (
    DocumentExportNoMutationStatements,
)
from statements.document_blank_title_save_statements import (
    DocumentBlankTitleSaveStatements,
)
from statements.document_content_only_save_statements import (
    DocumentContentOnlySaveStatements,
)


@pytest_asyncio.fixture
def document_export_statements(application_client):
    return DocumentExportStatements(application_client)


@pytest_asyncio.fixture
def document_export_format_statements(application_client):
    return DocumentExportFormatStatements(application_client)


@pytest_asyncio.fixture
def document_export_docx_statements(application_client):
    return DocumentExportDocxStatements(application_client)


@pytest_asyncio.fixture
def document_export_filename_statements(application_client):
    return DocumentExportFilenameStatements(application_client)


@pytest_asyncio.fixture
def document_export_no_mutation_statements(application_client):
    return DocumentExportNoMutationStatements(application_client)


@pytest_asyncio.fixture
def document_blank_title_save_statements(application_client):
    return DocumentBlankTitleSaveStatements(application_client)


@pytest_asyncio.fixture
def document_content_only_save_statements(application_client):
    return DocumentContentOnlySaveStatements(application_client)
