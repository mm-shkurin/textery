"""Backend setup Statements for the story-10 editor scenarios.

Kept separate from the page Statements on purpose (frontend-rules, "Selenium Tests"): page
Statements own browser interactions only, and all backend setup goes through a Statements class
the test injects directly rather than being delegated through the page DSL. The test therefore
reads its Given from here and its When/Then from `PaginationMeasuringStatements`.
"""

from statements.frontend.editor.live_document_setup import SeededDocument, seed_saved_document


class EditorDocumentStatements:
    """Establish the "a document exists, owned by the browser's user" precondition."""

    def given_a_saved_document(self) -> SeededDocument:
        """A fresh account with exactly one saved document, returned with its session.

        The session travels back to the test because the browser must sign in as THIS owner —
        the document and the identity that can see it are one precondition, not two.
        """
        return seed_saved_document()
