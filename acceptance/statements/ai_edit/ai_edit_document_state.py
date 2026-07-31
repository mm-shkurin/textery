"""One document read whole — its body plus its whole revision page — in one place.

Both halves are needed to answer "no new version was created": the document body carries
`version`, `content` and `updated_at`, and the revision page catches a restore that wrote
its revision row before losing the version CAS.

Every read here is pinned to 200 before its body is looked at. That matters most for the
BASELINE reads: an aftermath asserted as `after == before` is worth nothing if `before`
was itself an unvalidated error body, because two equal error bodies would agree.
"""

from dataclasses import dataclass

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.ai_edit import ai_edit_document_seed as seed
from statements.ai_edit.ai_edit_http_status import OK_STATUS


@dataclass(frozen=True)
class DocumentState:
    """A document and its revision page, read as the document's own owner."""

    document_id: str
    document: RawResponseDto
    revisions: RawResponseDto


async def read_state(
    client: DocumentEditClient, token: str, document_id: str, context: str
) -> DocumentState:
    return DocumentState(
        document_id=document_id,
        document=await seed.read_document(client, token, document_id),
        revisions=await read_revisions(client, token, document_id, context),
    )


async def read_revisions(
    client: DocumentEditClient, token: str, document_id: str, context: str
) -> RawResponseDto:
    response = await client.list_revisions(token, document_id)
    assert_revision_page_read_back_ok(response, document_id, context)
    return response


def assert_revision_page_read_back_ok(
    response: RawResponseDto, document_id: str, context: str
) -> None:
    """The revision-page read-back expectation, stated once for scenario 1.3.

    It consolidated the two spellings 1.3 itself carried — the baseline read and the
    aftermath read — which is the same drift risk that put the refusal envelope in a
    single shared function. It deliberately does NOT consolidate the other read-back
    asserts in the DSL: `ai_edit_document_seed.read_document` and the seeds' own
    "expected 200 reading ..." messages each carry setup-specific context, and a
    `document_seed` -> `document_state` dependency would close an import cycle.
    """
    assert response.status_code == OK_STATUS, (
        f"expected {OK_STATUS} with the owner reading their own revision page for "
        f"document {document_id} {context}, got status_code={response.status_code}, "
        f"body={response.text!r}"
    )
