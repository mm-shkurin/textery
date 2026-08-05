from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from access.project.project_feed_storage import SqlAlchemyProjectFeedRepository
from auth.account import Account
from document.document import Document
from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest

MISSING_OWNER_REFUSAL = (
    "list_feed requires a resolved owner_id: None would drop the owner predicate "
    "and read every account's rows"
)

_FEED_IS_OWNER_SCOPED = "the caller's feed must hold their own document and no one else's"

_ROW_CARRIES_THE_CONTRACT_FIELDS = (
    "every ProjectItem field must be projected from the document row -- kind, "
    "title, preview, document_type, status, retryable and both timestamps"
)

_TIMESTAMPS_CARRY_AN_OFFSET = (
    "both feed timestamps must stay tz-aware: the contract serializes UTC "
    "ISO-8601 with an explicit offset, and a naive datetime cannot"
)

_TIMESTAMPS_ARE_THE_STORED_INSTANTS = (
    "the row's timestamps must be the document's own, not a placeholder instant"
)

# The seeded document's values, stated here rather than read back off the entity
# the test itself built. `document.status` as an expectation is a mirror: it echoes
# `Document.create`'s own hardcoded default, so both sides of the equality move
# together and the feed's projection of that column is never actually pinned.
SEEDED_DOCUMENT_TYPE = "эссе"
SEEDED_STATUS = "draft"
SEEDED_CREATED_AT = datetime(2026, 3, 1, 9, 15, 0, tzinfo=UTC)
# Deliberately NOT equal to SEEDED_CREATED_AT. `Document.create` sets
# `updated_at=created_at`, so a projection that emitted the created column twice
# would satisfy a same-instant expectation and never be caught. Two distinct
# instants make the two columns tell each other apart.
SEEDED_UPDATED_AT = SEEDED_CREATED_AT + timedelta(minutes=37)

_REFUSAL_NAMES_THE_MISSING_OWNER = (
    "the refusal must name the unresolved owner as the reason, so a log line "
    "cannot be read as an empty feed"
)


class ProjectFeedStorageStatements:
    """DSL for the feed read model's storage adapter.

    The write half deliberately goes through `SqlAlchemyDocumentStorage` -- the
    port the create-document usecase writes through -- while the read half goes
    through `SqlAlchemyProjectFeedRepository`. That write-here-read-there shape is
    the point: a same-port round-trip would only pin one storage's own mapping and
    would leave the cross-usecase flow untested until acceptance.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = SqlAlchemyDocumentStorage(session)
        self._accounts = SqlAlchemyAccountRepository(session)
        self._feed = SqlAlchemyProjectFeedRepository(session)

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

    async def given_a_document_written_by_its_owner(self, owner_id: UUID) -> Document:
        """Write through the create-document usecase's own storage port.

        The instants are fixed, not `now()`: the row assertion states them as
        literals, and `updated_at` is nudged off `created_at` after construction
        because `Document.create` deliberately sets the two equal.
        """
        document = Document.create(
            owner_id=owner_id,
            document_type=SEEDED_DOCUMENT_TYPE,
            idempotency_key=f"key-{uuid4()}",
            created_at=SEEDED_CREATED_AT,
        )
        document.updated_at = SEEDED_UPDATED_AT
        await self._documents.save_new(document)
        await self._session.commit()
        return document

    async def list_feed(self, owner_id: UUID) -> ProjectPage:
        # The read is a genuine SELECT, not an identity-map hit: the session is
        # expire_on_commit=False, so an instance still resident would answer from
        # the values Python wrote rather than the bytes Postgres holds -- and an
        # owner predicate that never reached SQL would still look correct.
        self._session.expire_all()
        return await self._feed.list_feed(owner_id, ProjectPageRequest())

    def assert_feed_holds_only(self, page: ProjectPage, document: Document) -> None:
        # The ids alone, deliberately. This statement's claim is the owner
        # predicate: whose rows came back, not what each row carries. It used to
        # compare whole pages against `unprojected_row` -- a factory imported from
        # the module under test -- so both sides of the equality were one code path
        # and the assertion had collapsed to `document.id == row_id`. The row's
        # nine projected fields are pinned by `assert_row_is_projected_from` below,
        # against an expectation built here in the test tree.
        assert tuple(item.id for item in page.items) == (document.id,), _FEED_IS_OWNER_SCOPED

    def assert_row_is_projected_from(self, page: ProjectPage, document: Document) -> None:
        """Every contract field of the row, stated as literals by the test itself.

        The expectation is constructed here rather than imported from
        `access.project.project_feed_storage`, so the projection has an
        independent statement of what it owes: `kind` is the literal the source
        table implies, `preview` is `''` for a document whose content is empty,
        `retryable` is false for every document, and `title` stays **None** --
        `Document.create` never sets one, the contract declares `title` nullable
        and omits it from `required`, and coercing NULL to `''` would destroy the
        null/blank distinction scenario 3.3's `title_asc` ordering depends on.
        """
        expected = ProjectItem(
            kind="document",
            id=document.id,
            title=None,
            preview="",
            document_type=SEEDED_DOCUMENT_TYPE,
            status=SEEDED_STATUS,
            retryable=False,
            created_at=SEEDED_CREATED_AT,
            updated_at=SEEDED_UPDATED_AT,
        )
        assert page.items == (expected,), _ROW_CARRIES_THE_CONTRACT_FIELDS

    def assert_row_timestamps_are_tz_aware(self, page: ProjectPage) -> None:
        """Both instants, and the exact offset each carries.

        Pinned separately because nothing else can catch it: the usecase's shape
        guard reflects over field names and defaults, never `field.type`, so a
        naive `datetime` handed back by the driver would leave every other test
        green while breaking the contract's "UTC ISO-8601 with explicit offset".

        The offset is asserted as zero, not merely as present: the contract
        serializes UTC, and a row arriving as `+05:00` names the same instant
        while rendering a different wall clock -- `tzinfo is not None` would wave
        it through.
        """
        (row,) = page.items
        assert (
            row.created_at,
            row.created_at.utcoffset(),
            row.updated_at,
            row.updated_at.utcoffset(),
        ) == (
            SEEDED_CREATED_AT,
            timedelta(0),
            SEEDED_UPDATED_AT,
            timedelta(0),
        ), f"{_TIMESTAMPS_CARRY_AN_OFFSET}; {_TIMESTAMPS_ARE_THE_STORED_INSTANTS}"

    async def assert_feed_refuses_an_unresolved_owner(self) -> None:
        """Call the port the way an unresolved caller would. Must not be served."""
        with pytest.raises(ValueError) as refusal:
            await self._feed.list_feed(None, ProjectPageRequest())

        assert str(refusal.value) == MISSING_OWNER_REFUSAL, _REFUSAL_NAMES_THE_MISSING_OWNER
