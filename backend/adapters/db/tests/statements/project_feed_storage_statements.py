from datetime import UTC, datetime
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

_REFUSAL_NAMES_THE_MISSING_OWNER = (
    "the refusal must name the unresolved owner as the reason, so a log line "
    "cannot be read as an empty feed"
)


class ProjectFeedStatements:
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
        """Write through the create-document usecase's own storage port."""
        document = Document.create(
            owner_id=owner_id,
            document_type="эссе",
            idempotency_key=f"key-{uuid4()}",
            created_at=datetime.now(UTC),
        )
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
        # Compared as a whole page, not as `page.items`: `ProjectPage` grows `page`,
        # `limit` and `total` with the paging scenarios, and an assertion that reaches
        # past the page into one field would keep passing while those arrive unchecked.
        expected = ProjectPage(items=(ProjectItem(id=document.id),))
        assert page == expected, _FEED_IS_OWNER_SCOPED

    async def assert_feed_refuses_an_unresolved_owner(self) -> None:
        """Call the port the way an unresolved caller would. Must not be served."""
        with pytest.raises(ValueError) as refusal:
            await self._feed.list_feed(None, ProjectPageRequest())

        assert str(refusal.value) == MISSING_OWNER_REFUSAL, _REFUSAL_NAMES_THE_MISSING_OWNER
