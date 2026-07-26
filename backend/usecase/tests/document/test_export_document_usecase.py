"""ExportDocument: the read side of exporting to PDF/DOCX.

Scenario 1.1 -- exporting a document id that does not exist is refused. The
usecase returns None (the refusal signal the router turns into a 404) rather
than raising, mirroring GetDocument: absent and foreign both collapse to None
because the repository filters on owner_id in SQL.
"""

from uuid import uuid4

import pytest

from document.export_document import ExportDocument
from statements.document_fakes import FakeDocumentRepository


class TestExportDocument:
    async def test_should_answer_none_for_a_non_existent_document(self):
        found = await ExportDocument(FakeDocumentRepository()).execute(
            document_id=uuid4(), owner_id=uuid4()
        )

        assert found is None
