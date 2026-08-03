from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import ClassVar

from clients.application.dto.document.get_document_response_dto import (
    GetDocumentResponseDto,
)
from statements.document_export_statements import (
    SUPPORTED_DOCUMENT_TYPE,
    DocumentExportStatements,
)

# The whole state a freshly created document is in, pinned as literals rather than
# echoed back from the response. Document.create hardcodes them (domain/document.py:
# status=draft, content="", version=1), so an assertion that read them out of the very
# response under test would pass for any value the server chose to invent.
DRAFT_STATUS = "draft"
FRESH_DOCUMENT_CONTENT = ""
VERSION_AFTER_CREATE = 1
# Slack on the created_at/updated_at window: the stamp is taken by the server clock,
# which may sit a few seconds either side of the test runner's. Bounding the timestamp
# to the arrange window (rather than checking it is merely present) still fails a
# stamp from a past import, a fixed epoch, or a future date.
CLOCK_SKEW_TOLERANCE = timedelta(seconds=5)


@dataclass(frozen=True)
class NeverConfiguredDocumentRead:
    """The read under test plus what the arrange knows the answer must contain.

    The created `document_id` and the wall-clock window bracketing the creation are
    captured here so the Then-phase can pin them exactly. Without this the response's
    own id and timestamps would be unpinnable, and a read that returned some *other*
    document's body would pass.
    """

    response: GetDocumentResponseDto
    document_id: str
    stamped_no_earlier_than: datetime
    stamped_no_later_than: datetime


class DocumentPageSettingsReadStatements(DocumentExportStatements):
    """Scenario 2.1 statements (a never-configured document reads as unconfigured).

    Subclasses DocumentExportStatements to reuse `_authenticated_access_token` and
    `_create_document_owned_by` — the same account+document arrange every document
    scenario shares, exactly as DocumentExportNoMutationStatements does. Kept in its
    own module so both files stay under the 200-line cap.
    """

    # The read-side page-settings key on GET /documents/{id}
    # (api-specs/documents_get.yaml, DocumentResponse.page_settings).
    PAGE_SETTINGS_FIELD: ClassVar[str] = "page_settings"

    # Every property DocumentResponse defines (documents_get.yaml lines 70-102), as an
    # exact set. Pinning the key set — rather than scanning the body for the nine known
    # PageSettings property names — is what forbids a materialized default in EITHER
    # shape: a nested object fails on the page_settings value, and a flattened
    # `page_size`/`margins_mm`/... fails as an unexpected key. It needs no copy of the
    # PageSettings schema to stay correct, so a key added to that schema later cannot
    # silently narrow this test.
    EXPECTED_BODY_KEYS: ClassVar[frozenset] = frozenset(
        {
            "document_id",
            "document_type",
            "status",
            "content",
            "version",
            "page_settings",
            "created_at",
            "updated_at",
        }
    )

    async def given_owner_reads_a_never_configured_document(
        self,
    ) -> NeverConfiguredDocumentRead:
        # A freshly created document has never had its page settings set: creation
        # carries no page_settings field at all (endpoints.md, "No page_settings on
        # POST /documents"), so the very first read is the never-configured read.
        #
        # The read itself is NOT pinned with assert_setup_ok here — it is the act, not
        # the arrange. Its status belongs in the Then-phase, where a regression to
        # 404/500 reads as a behaviour failure instead of a setup failure.
        access_token = await self._authenticated_access_token()
        stamped_no_earlier_than = datetime.now(timezone.utc) - CLOCK_SKEW_TOLERANCE
        document_id = await self._create_document_owned_by(access_token)
        response = await self._client.get_document(document_id, access_token)
        return NeverConfiguredDocumentRead(
            response=response,
            document_id=document_id,
            stamped_no_earlier_than=stamped_no_earlier_than,
            stamped_no_later_than=datetime.now(timezone.utc) + CLOCK_SKEW_TOLERANCE,
        )

    def assert_page_settings_reported_as_absent(
        self, read: NeverConfiguredDocumentRead
    ) -> None:
        # "Reported as absent" is an explicit null on a present key, not a missing
        # key: the field is declared nullable on DocumentResponse, so the client can
        # distinguish "never configured" from "this server does not know the field".
        body = self._body_of_the_successful_read(read)
        assert self.PAGE_SETTINGS_FIELD in body, (
            f"expected the document read to carry the {self.PAGE_SETTINGS_FIELD!r} "
            f"field, got body={body!r}"
        )
        assert body[self.PAGE_SETTINGS_FIELD] is None, (
            f"expected {self.PAGE_SETTINGS_FIELD!r} to be null on a never-configured "
            f"document, got {body[self.PAGE_SETTINGS_FIELD]!r}"
        )

    def assert_no_materialized_default_object(
        self, read: NeverConfiguredDocumentRead
    ) -> None:
        # The defaults must not be materialized anywhere in the response. Materializing
        # them would freeze today's preset into every old document and make "never
        # configured" indistinguishable from "configured to the current defaults".
        #
        # Pinned as the complete document view rather than as a hunt for page-settings
        # keys: the exact key set rules out every leaked default (nested or flattened),
        # and the exact field values rule out the other half of the failure — a server
        # that suppressed page_settings by returning a stripped or wrong document.
        body = self._body_of_the_successful_read(read)
        assert set(body) == self.EXPECTED_BODY_KEYS, (
            f"expected the never-configured document read to carry exactly the "
            f"DocumentResponse keys {sorted(self.EXPECTED_BODY_KEYS)!r} — any extra key "
            f"is a materialized page-settings default flattened onto the body — got "
            f"{sorted(body)!r}"
        )
        expected = {
            "document_id": read.document_id,
            "document_type": SUPPORTED_DOCUMENT_TYPE,
            "status": DRAFT_STATUS,
            "content": FRESH_DOCUMENT_CONTENT,
            "version": VERSION_AFTER_CREATE,
            self.PAGE_SETTINGS_FIELD: None,
        }
        assert {key: body[key] for key in expected} == expected, (
            f"expected the never-configured document to read back as the untouched "
            f"fresh document {expected!r}, got body={body!r}"
        )
        self._assert_stamped_within_the_arrange_window(body, read)

    def _assert_stamped_within_the_arrange_window(
        self, body: dict, read: NeverConfiguredDocumentRead
    ) -> None:
        # The two timestamps are the only fields the arrange cannot pin to a literal.
        # They are still deterministic within a bound: both must fall inside the window
        # bracketing the creation call, and — since Document.create sets
        # updated_at = created_at and nothing has saved the document since — they must
        # be equal to each other.
        created_at = self._parsed_timestamp(body, "created_at")
        updated_at = self._parsed_timestamp(body, "updated_at")
        for field, stamp in (("created_at", created_at), ("updated_at", updated_at)):
            assert read.stamped_no_earlier_than <= stamp <= read.stamped_no_later_than, (
                f"expected {field} to be stamped while the document was being created, "
                f"between {read.stamped_no_earlier_than.isoformat()} and "
                f"{read.stamped_no_later_than.isoformat()}, got {stamp.isoformat()}"
            )
        assert updated_at == created_at, (
            f"expected a never-saved document to carry updated_at equal to created_at, "
            f"got created_at={created_at.isoformat()}, updated_at={updated_at.isoformat()}"
        )

    @staticmethod
    def _parsed_timestamp(body: dict, field: str) -> datetime:
        raw = body[field]
        try:
            stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            raise AssertionError(
                f"expected {field} to be an ISO-8601 timestamp, got {raw!r}"
            )
        # A naive stamp is UTC by contract (documents_get.yaml declares date-time and
        # the server stamps in UTC); attaching the zone keeps the window comparison
        # from raising on mixed awareness instead of failing with a readable message.
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)

    @staticmethod
    def _body_of_the_successful_read(read: NeverConfiguredDocumentRead) -> dict:
        # The guard half of every assertion below. Pinning the status here — instead of
        # coalescing a missing body to {} — means a 404/500 read fails as "the read was
        # refused" rather than as the misleading "page_settings field is missing".
        response = read.response
        assert response.status_code == 200, (
            f"expected the owner's read of their own never-configured document to "
            f"succeed with 200, got status_code={response.status_code}, "
            f"body={response.body!r}"
        )
        assert isinstance(response.body, dict), (
            f"expected the read to carry a JSON document body, got "
            f"body={response.body!r}"
        )
        return response.body
