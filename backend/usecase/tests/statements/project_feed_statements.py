"""Test DSL for scenario 1.1 -- the feed is owner-scoped.

Given an authenticated user with documents
And another account with its own documents
When they request their projects
Then only their own documents are returned
And the other account's documents are absent.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from fake.auth.fake_clock import FakeClock
from fake.project.fake_project_feed_repository import (
    FakeProjectFeedRepository,
    FakeSearchSlots,
)
from project.list_projects import ListProjects
from project.project_item import ProjectItem
from project.project_page import ProjectPage, ProjectPageRequest
from shared.exceptions import ValidationException

_FIXED_NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)

# Stated once so the arrangement and the count assertion cannot drift apart.
_DOCUMENTS_PER_ACCOUNT = 2

# The test defines the refusal, so green has a fixed target rather than a free
# choice. Deliberately says nothing about *why* the owner could not be resolved:
# a caller who learns whether the token was missing, expired or of the wrong type
# learns more than the 401 contract concedes.
_UNAUTHENTICATED_ERROR_CODE = "UNAUTHENTICATED"
_UNAUTHENTICATED_MESSAGE = "Authentication is required to view your projects."


@dataclass(frozen=True)
class ServedFeed:
    """What the caller got back, plus what they were entitled to."""

    page: ProjectPage
    own_items: tuple[ProjectItem, ...]
    other_accounts_items: tuple[ProjectItem, ...]


class ProjectFeedStatements:
    def __init__(self) -> None:
        self._repository = FakeProjectFeedRepository()
        self._search_slots = FakeSearchSlots()
        self._usecase = ListProjects(
            project_feed_repository=self._repository,
            search_slots=self._search_slots,
            clock=FakeClock(_FIXED_NOW),
        )
        self._caller_id = uuid4()
        self._own_items: tuple[ProjectItem, ...] = ()
        self._other_accounts_items: tuple[ProjectItem, ...] = ()

    def given_two_accounts_each_with_documents(self) -> None:
        self._own_items = self._documents_of(self._caller_id, count=_DOCUMENTS_PER_ACCOUNT)
        self._other_accounts_items = self._documents_of(uuid4(), count=_DOCUMENTS_PER_ACCOUNT)

    async def when_the_caller_requests_their_projects(self) -> ServedFeed:
        page = await self._usecase.execute(owner_id=self._caller_id, request=ProjectPageRequest())
        return ServedFeed(
            page=page,
            own_items=self._own_items,
            other_accounts_items=self._other_accounts_items,
        )

    async def when_an_unresolved_caller_requests_their_projects(self) -> ValidationException:
        with pytest.raises(ValidationException) as excinfo:
            await self._usecase.execute(owner_id=cast(UUID, None), request=ProjectPageRequest())
        return excinfo.value

    def assert_exactly_the_callers_own_items_are_returned(self, feed: ServedFeed) -> None:
        # Guard the guard, as the absence assertion does for the other account: if
        # the caller were never seeded, the multiset comparison below would compare
        # empty to empty and pass while proving nothing. This claims the
        # *arrangement*, which is why it reads `own_items` and not `page.items`.
        assert len(feed.own_items) == _DOCUMENTS_PER_ACCOUNT, (
            "the caller must actually own rows, or this proves nothing"
        )
        # Multiset equality in one comparison: a row the projection suppressed, a
        # row it invented, and a row it served twice each surface as a difference.
        # Set equality would swallow the duplicate; a length check on the served
        # page would swallow a substitution -- and, given this comparison, could
        # never fail on its own. Order is deliberately not pinned here -- `sort` is
        # scenario 2.x's claim, and asserting it now would make this test fail for
        # a reason it does not own.
        assert Counter(feed.page.items) == Counter(feed.own_items), (
            "the feed must serve exactly the caller's own rows, each exactly once"
        )

    def assert_the_feed_was_queried_once_scoped_to_the_caller(self) -> None:
        # Owner scoping is a property of the *call*, not only of the rows that
        # came back. Without this, a usecase that queried unscoped and filtered in
        # Python would pass -- and that is precisely the shape the read-model
        # decision pushed into the statement.
        assert self._repository.calls == [(self._caller_id, ProjectPageRequest())], (
            "exactly one feed query, scoped to the caller, with the caller's request"
        )

    def assert_the_other_accounts_documents_are_absent(self, feed: ServedFeed) -> None:
        # Guard the guard: if the other account were never seeded, every absence
        # assertion below would pass vacuously and the scenario would prove
        # nothing at all.
        assert len(feed.other_accounts_items) == _DOCUMENTS_PER_ACCOUNT, (
            "the other account must actually own rows, or this proves nothing"
        )
        assert set(feed.page.items).isdisjoint(feed.other_accounts_items), (
            "another account's documents must never appear in the caller's feed"
        )

    def assert_the_refusal_is_unauthenticated(self, refusal: ValidationException) -> None:
        # Both fields, as a tuple -- the sibling convention. The message is part of
        # the contract the ADR pinned as `{error_code, message}`, so a refusal that
        # carries the right code with the wrong (or a leaking) message must go red.
        assert (refusal.error_code, refusal.message) == (
            _UNAUTHENTICATED_ERROR_CODE,
            _UNAUTHENTICATED_MESSAGE,
        )

    def assert_the_feed_was_never_queried(self) -> None:
        # The heart of the guard: an unresolved owner must fail closed, never
        # become an unscoped read served as a well-formed empty 200.
        assert self._repository.calls == [], (
            "the feed statement must not run when the owner could not be resolved"
        )

    def _documents_of(self, owner_id: UUID, count: int) -> tuple[ProjectItem, ...]:
        items = tuple(ProjectItem(id=uuid4()) for _ in range(count))
        self._repository.seed(owner_id, *items)
        return items
