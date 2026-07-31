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
    assert_read_back_ok(response, document_id, "revision page", context)
    return response


def assert_read_back_ok(
    response: RawResponseDto, document_id: str, what: str, context: str
) -> None:
    """The one read-back expectation, stated once.

    It was previously written three times over — in the revision seed, in the document
    seed and again in scenario 1.3's assertions — which is the same drift risk that put
    the refusal envelope in a single shared function.
    """
    assert response.status_code == OK_STATUS, (
        f"expected {OK_STATUS} with the owner reading their own {what} for document "
        f"{document_id} {context}, got status_code={response.status_code}, "
        f"body={response.text!r}"
    )
