import ast
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from auth.account import Account
from document.document import Document
from document.page_settings import PageSettings
from document.title_update import TitleUpdate
from statements.document_storage_assertions import DocumentStorageAssertions
from statements.page_settings_fakes import configured_page_settings


class DocumentStorageStatements(DocumentStorageAssertions):
    """DSL for the document storage adapter's tests -- the arrange and act half.

    The assertions live on `DocumentStorageAssertions`, inherited rather than
    delegated so every call site stays `document_storage_statements.assert_*`.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session
        self._storage = SqlAlchemyDocumentStorage(session)
        self._accounts = SqlAlchemyAccountRepository(session)

    async def given_an_account(self) -> UUID:
        # documents.owner_id is a real FK, so a document needs a real account row.
        account = Account.create(
            id=uuid4(),
            email=f"owner-{uuid4()}@example.com",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        await self._accounts.save(account)
        return account.id

    async def given_a_saved_document(self, owner_id: UUID, idempotency_key: str = "") -> Document:
        document = Document.create(
            owner_id=owner_id,
            document_type="эссе",
            idempotency_key=idempotency_key or f"key-{uuid4()}",
            created_at=datetime.now(UTC),
        )
        await self._storage.save_new(document)
        await self._session.commit()
        return document

    async def find_by_id_and_owner(self, document_id: UUID, owner_id: UUID) -> Document | None:
        return await self._storage.find_by_id_and_owner(document_id, owner_id)

    async def find_by_idempotency_key(self, owner_id: UUID, key: str) -> Document | None:
        return await self._storage.find_by_idempotency_key(owner_id, key)

    async def save_content_if_version_matches(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        expected_version: int,
        title: TitleUpdate,
    ) -> Document | None:
        # The signature MIRRORS the port's `title` parameter exactly -- required, no
        # default, `TitleUpdate` only -- and the value is forwarded
        # UNCHANGED -- constructing or unwrapping a TitleUpdate here would launder
        # the very thing under test. A DSL that accepted a raw `str` would let a
        # test make a call no production caller can make, and would quietly lift a
        # future `title=""` back into the `SET title = ''` shape the adapter
        # deleted by construction. `TitleUpdate.preserve()` is the content-only
        # autosave path (title omitted from the SET list), and it is spelled at
        # every call site rather than defaulted here: the port has no default, so
        # neither does its DSL mirror.
        self._last_updated_at = datetime.now(UTC)
        return await self._storage.save_content_if_version_matches(
            document_id=document_id,
            owner_id=owner_id,
            content=content,
            expected_version=expected_version,
            updated_at=self._last_updated_at,
            title=title,
        )

    async def given_a_configured_document(self, owner_id: UUID) -> Document:
        """A row whose `page_settings` column holds a full nine-key object.

        Seeded in raw SQL rather than through `save_new`, deliberately. Scenario
        2.1 is the READ path; routing the seed through the mapper's write half
        would let a mapper that is symmetrically wrong in both directions --
        writing and reading the same six keys, say -- round-trip its own mistake
        and report green. The blob is derived from the value object with
        `asdict`, not hand-written, so `page_settings_fakes` stays the single
        place that says what "configured" means.

        The fake is sourced here rather than passed in by the test. It was being
        called twice at the call site -- once to seed and once as the expectation
        -- which put a non-DSL factory in the test body for no gain: there is one
        configured object in this story and both halves must be the same one.
        `the_configured_page_settings()` below is what the assertion compares to.
        """
        document = await self.given_a_saved_document(owner_id)
        await self._seed_stored_page_settings(
            document.id, json.dumps(asdict(self.the_configured_page_settings()))
        )
        return document

    async def given_a_document_configured_to_nothing(self, owner_id: UUID) -> Document:
        """A row whose column holds an empty *configured* object, not SQL NULL.

        The `"{}"` storage-format literal lives here rather than in the test body:
        it is how the blob is spelled on the wire to Postgres, which is a fact
        about storage, not about what the test is asserting.
        """
        document = await self.given_a_saved_document(owner_id)
        await self._seed_stored_page_settings(document.id, "{}")
        return document

    def the_configured_page_settings(self) -> PageSettings:
        """The one off-preset object this suite seeds and expects, shared with the
        domain and usecase layers via `page_settings_fakes`."""
        return configured_page_settings()

    async def _seed_stored_page_settings(self, document_id: UUID, blob: str | None) -> None:
        await self._session.execute(
            text("UPDATE documents SET page_settings = CAST(:blob AS jsonb) WHERE id = :id"),
            {"blob": blob, "id": document_id},
        )

    async def stored_page_settings_column(self, document_id: UUID) -> Any:
        """The column exactly as Postgres holds it -- SQL NULL comes back as None.

        Read in raw SQL on purpose: the mapper is the thing under test in the
        sibling guard, so asking it what the column contains would be circular.
        """
        result = await self._session.execute(
            text("SELECT page_settings FROM documents WHERE id = :id"),
            {"id": document_id},
        )
        return result.scalar_one()

    async def page_settings_column_shape(self) -> tuple[str, str, str | None] | None:
        """`(data_type, is_nullable, column_default)` for the column, or None if absent."""
        result = await self._session.execute(
            text(
                "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = 'documents' AND column_name = 'page_settings'"
            )
        )
        row = result.first()
        return (row[0], row[1], row[2]) if row else None

    def page_settings_migration_upgrade_source(self) -> str | None:
        """The source of `upgrade()` in the revision that adds `documents.page_settings`.

        Read as text because the property under guard -- "this migration writes
        nothing into rows that already exist" -- is not observable in the database
        the suite connects to. That database is already at head, so every row any
        test can create post-dates the migration, and a data backfill is invisible
        to every query. Actually re-running the migration against a populated table
        would mean driving alembic through a downgrade on a database this suite
        shares across tests, dropping a column out from under whatever else is
        running; the revision script is the honest place to observe it instead.
        """
        versions = Path(__file__).resolve().parents[2] / "migrations" / "versions"
        for revision in sorted(versions.glob("*.py")):
            source = revision.read_text(encoding="utf-8")
            if "page_settings" not in source:
                continue
            upgrade = next(
                (
                    node
                    for node in ast.parse(source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
                ),
                None,
            )
            if upgrade is not None:
                return ast.get_source_segment(source, upgrade)
        return None

    async def page_settings_read_outcome(
        self, document_id: UUID, owner_id: UUID
    ) -> tuple[str, str]:
        """What reading this row's page settings *does*, as a comparable token.

        The `try` is not defensive coding. `PageSettings` has nine required fields
        and `from_stored` belongs to 2.3/2.4, so there is no domain value that can
        hold a stored `{}` today and the read may legitimately raise. This method
        may therefore not presuppose a return value.

        It catches `TypeError`/`ValueError` ONLY -- the two a nine-required-field
        constructor raises when handed an empty mapping. A bare `except Exception`
        was laundering every other failure into a token: an `AttributeError` from a
        genuine mapper bug, a SQLAlchemy error from an unrelated column, a mistyped
        DSL call, all came back as `("raised", ...)` and the assertion, which only
        required the two tokens to differ, went green on them. Everything outside
        those two now propagates and fails the test as the error it is.

        Which of the admissible tokens is correct is settled by
        `ADMISSIBLE_EMPTY_OBJECT_OUTCOMES` on the assertion side. The classification
        here is only the read's raw shape; the judgement is not made in this method.
        """
        try:
            document = await self.find_by_id_and_owner(document_id, owner_id)
        except (TypeError, ValueError) as error:
            return ("raised", type(error).__name__)
        if document is None:
            return ("read", "no-document")
        return ("read", "absent" if document.page_settings is None else "present")

    async def commit(self) -> None:
        await self._session.commit()

    def expire_identity_map(self) -> None:
        """Force the next find to be a genuine SELECT, not an identity-map hit.

        The session is expire_on_commit=False, so an unexpired instance in the
        identity map is handed back with its IN-MEMORY values and a read-back
        asserts x == x. Measured, that staleness is real: holding a strong
        reference to the model and corrupting the row in raw SQL, the find returns
        the stale `''` while a find after expire_all() returns the corrupted value.

        It does NOT currently bite these tests: SQLAlchemy's identity map holds WEAK
        references, and neither `save_new` nor the CAS keeps a reference to the model
        (`model.to_domain()` is returned and the local dies), so the instance is
        collected and the map is empty by the time the find runs. That makes today's
        reads genuine by refcounting accident. This call turns the accident into a
        stated guarantee -- it costs one no-op and it is what keeps the read honest
        if anyone ever retains the model.
        """
        self._session.expire_all()
