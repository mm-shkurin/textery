import inspect
from datetime import datetime, timezone
from uuid import UUID, uuid4

from document.document import DRAFT_STATUS, Document


class TestDocumentCreate:
    """Scenario 2.1: Creating a manual document returns immediately, empty, no Generation.

    Given a valid manual-document creation request for a supported document type
    When the document is created
    Then its status is "draft" with empty content, at version 1
    """

    def test_should_create_an_empty_draft_at_version_one(self):
        owner_id = uuid4()
        created_at = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)

        document = Document.create(
            owner_id=owner_id,
            document_type="эссе",
            idempotency_key="key-1",
            created_at=created_at,
        )

        assert isinstance(document.id, UUID), f"id must be a server-generated UUID, got {document.id!r}"
        assert document.owner_id == owner_id
        assert document.document_type == "эссе"
        assert document.status == DRAFT_STATUS
        assert document.content == "", "a new document starts empty"
        assert document.version == 1, "version starts at 1 — it is the client's first CAS token"
        assert document.idempotency_key == "key-1"
        assert document.created_at == created_at
        assert document.updated_at == created_at, "updated_at equals created_at on creation"

    def test_should_generate_a_distinct_id_per_document(self):
        # Security 4.1: identifiers are not sequential or guessable from one another.
        ids = {
            Document.create(
                owner_id=uuid4(),
                document_type="доклад",
                idempotency_key=f"key-{index}",
                created_at=datetime.now(timezone.utc),
            ).id
            for index in range(50)
        }

        assert len(ids) == 50, "every created document must get its own id"
        assert all(document_id.version == 4 for document_id in ids), (
            "ids must be UUIDv4 (random), not v1 (host/time-derived) — v1 leaks MAC and clock "
            "and is partially predictable across consecutive creations"
        )


class TestDocumentMassAssignmentIsImpossibleBySignature:
    """Security 2.1 / Scenario 1.2: server-owned fields cannot be set by the client.

    This is asserted against the factory's *signature*, not its behaviour, and that
    is the point. Every other guard (a DTO that omits the field, a filter that pops
    it) can be bypassed by a future caller; a parameter that does not exist cannot
    be passed. If someone adds `status=` or `content=` here to make a test easier,
    this fails — which is the only warning the design gets.
    """

    def test_create_should_not_accept_any_server_owned_field(self):
        parameters = set(inspect.signature(Document.create).parameters)

        assert parameters == {"owner_id", "document_type", "idempotency_key", "created_at"}, (
            f"Document.create must expose only client-supplied and injected values; got {parameters}"
        )

    def test_create_should_not_accept_an_id(self):
        assert "id" not in inspect.signature(Document.create).parameters, (
            "an attacker-supplied id must be impossible to pass, not merely ignored"
        )
