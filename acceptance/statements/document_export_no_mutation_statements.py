from dataclasses import dataclass

from clients.application.dto.document.get_document_response_dto import GetDocumentResponseDto
from statements.document_export_statements import DocumentExportStatements


@dataclass(frozen=True)
class ExportMutationSnapshot:
    """A before/after pair of GET /documents/{id} responses bracketing one export.

    Captures the full document view on each side so the no-mutation assertion can
    pin version and the other mutation-visible fields (content, updated_at), not
    just the spec's named field in isolation.
    """

    before: GetDocumentResponseDto
    after: GetDocumentResponseDto


class DocumentExportNoMutationStatements(DocumentExportStatements):
    """Scenario 2.4 statements (export does not mutate the document).

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token` and
    `_create_document_owned_by`. Kept in its own module so the base export statements
    file stays under the 200-line cap.
    """

    async def given_owner_document_read_exported_and_reread(self) -> ExportMutationSnapshot:
        # A document owned by the caller at a known version: create it, read its
        # state, export it (exercising the pdf path), then read its state again.
        # Export is a GET with no persistence call, so the two reads must be
        # identical — this brackets the export to catch any accidental mutation.
        owner_access_token = await self._authenticated_access_token()
        document_id = await self._create_document_owned_by(owner_access_token)
        before = await self._client.get_document(document_id, owner_access_token)
        assert before.status_code == 200, (
            f"setup: expected 200 reading the owner's own document before export, got "
            f"status_code={before.status_code}, body={before.body}"
        )
        export_response = await self._client.export_document(
            document_id=document_id,
            export_format="pdf",
            access_token=owner_access_token,
        )
        assert export_response.status_code == 200, (
            f"setup: expected 200 exporting the owner's own document as pdf, got "
            f"status_code={export_response.status_code}, body={export_response.body}"
        )
        after = await self._client.get_document(document_id, owner_access_token)
        assert after.status_code == 200, (
            f"setup: expected 200 reading the owner's own document after export, got "
            f"status_code={after.status_code}, body={after.body}"
        )
        return ExportMutationSnapshot(before=before, after=after)

    def assert_version_unchanged(self, snapshot: ExportMutationSnapshot) -> None:
        # The spec's named guarantee: the version after export equals the version
        # before, by exact integer equality — not merely non-null.
        version_before = (snapshot.before.body or {}).get("version")
        version_after = (snapshot.after.body or {}).get("version")
        assert version_before is not None, (
            f"setup: expected a version in the pre-export document view, got "
            f"body={snapshot.before.body!r}"
        )
        assert version_after == version_before, (
            f"expected the document version to be unchanged by export, but it went "
            f"from {version_before!r} to {version_after!r}"
        )

    def assert_not_mutated(self, snapshot: ExportMutationSnapshot) -> None:
        # No mutation, pinned broadly: content and updated_at are the other
        # mutation-visible fields, so an export that rewrote content or touched the
        # timestamp while leaving version alone cannot slip through.
        before_body = snapshot.before.body or {}
        after_body = snapshot.after.body or {}
        assert after_body.get("content") == before_body.get("content"), (
            f"expected export to leave content unchanged, but it went from "
            f"{before_body.get('content')!r} to {after_body.get('content')!r}"
        )
        assert after_body.get("updated_at") == before_body.get("updated_at"), (
            f"expected export to leave updated_at unchanged, but it went from "
            f"{before_body.get('updated_at')!r} to {after_body.get('updated_at')!r}"
        )
