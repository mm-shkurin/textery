from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from access.auth.account_storage import SqlAlchemyAccountRepository
from access.document.document_storage import SqlAlchemyDocumentStorage
from access.project.project_feed_storage import SqlAlchemyProjectFeedRepository
from auth.account import Account
from document.document import Document
from project.project_page import ProjectPage, ProjectPageRequest
from statements.project_feed_row_expectations import (
    SEEDED_CONTENT,
    SEEDED_CREATED_AT,
    SEEDED_DOCUMENT_TYPE,
    SEEDED_TITLE,
    SEEDED_UPDATED_AT,
    ProjectFeedRowExpectations,
)

# Hand-written, and deliberately NOT imported from
# `access.project.project_feed_storage`, which holds a constant of the same value:
# importing it would make the expectation and the value under test one symbol, and a
# refusal raised with the wrong message would stay green. Underscore-prefixed like
# every other message constant here, so the name cannot be mistaken for the
# production one at a glance.
_MISSING_OWNER_REFUSAL = (
    "list_feed requires a resolved owner_id: None would drop the owner predicate "
    "and read every account's rows"
)

_FEED_IS_OWNER_SCOPED = "the caller's feed must hold their own document and no one else's"

_REFUSAL_NAMES_THE_MISSING_OWNER = (
    "the refusal must name the unresolved owner as the reason, so a log line "
    "cannot be read as an empty feed"
)


class ProjectFeedStorageStatements(ProjectFeedRowExpectations):
    """DSL for the feed read model's storage adapter.

    The write half deliberately goes through `SqlAlchemyDocumentStorage` -- the
    port the create-document usecase writes through -- while the read half goes
    through `SqlAlchemyProjectFeedRepository`. That write-here-read-there shape is
    the point: a same-port round-trip would only pin one storage's own mapping and
    would leave the cross-usecase flow untested until acceptance.

    Row-level expectations live in `ProjectFeedRowExpectations`, mixed in above --
    a 200-line-limit split, not a seam.
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
        """Write an untitled, empty-content draft through the create-document port.

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
        return await self._save(document)

    async def given_a_titled_document_written_by_its_owner(self, owner_id: UUID) -> Document:
        """Write a draft that actually carries a title and content.

        `Document.create_from_generation` is the production path that produces
        one: `Document.create` refuses a `content` argument as a mass-assignment
        guard, so it cannot seed text and every document it makes has
        `title=None, content=''` -- values indistinguishable from a projection
        that never reads the two columns at all.

        Seeded for an account of its own rather than alongside the empty-content
        document: 1.1 owns neither ordering nor paging, so a two-row page would
        force this test to assert a sequence whose order no scenario has yet
        specified. Each seeded document therefore gets a one-row page, and both
        cases hold independently.
        """
        document = Document.create_from_generation(
            owner_id=owner_id,
            document_type=SEEDED_DOCUMENT_TYPE,
            generation_id=uuid4(),
            content=SEEDED_CONTENT,
            title=SEEDED_TITLE,
            idempotency_key=f"key-{uuid4()}",
            created_at=SEEDED_CREATED_AT,
        )
        return await self._save(document)

    async def _save(self, document: Document) -> Document:
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
        # projected fields are pinned by the whole-page equalities in
        # `ProjectFeedRowExpectations`, against expectations built in the test tree.
        assert tuple(item.id for item in page.items) == (document.id,), _FEED_IS_OWNER_SCOPED

    async def assert_feed_refuses_an_unresolved_owner(self) -> None:
        """Call the port the way an unresolved caller would. Must not be served."""
        with pytest.raises(ValueError) as refusal:
            # The ignore is the point of the test, not a way around it: `list_feed`
            # is annotated `owner_id: UUID`, and this pins that it *also* refuses at
            # runtime. Annotations are erased at run time, so an unresolved caller
            # reaching this port is a real production shape that no type check can
            # prevent -- which is why the guard exists and why proving it needs a
            # call the type checker would otherwise reject.
            await self._feed.list_feed(None, ProjectPageRequest())  # type: ignore[arg-type]

        assert str(refusal.value) == _MISSING_OWNER_REFUSAL, _REFUSAL_NAMES_THE_MISSING_OWNER
