"""Statements for the projects feed (`GET /api/v1/projects`), scenario 1.1.

Setup goes through the public API only: two accounts are registered and each creates
one document, then both request their own feed. Asserting BOTH feeds is deliberate --
"the caller sees only their own" would also be satisfied by an endpoint that returns an
empty page to everyone, so the other account's feed is the positive control that makes
the isolation claim real.

Each feed is asserted as a whole parsed envelope compared against a constructed
expected one, not field by field: every `ProjectItem` field the contract declares is
therefore pinned, and a row that appeared with the right id but the wrong status,
document_type or timestamp fails here rather than passing an id-only check.

The `Cache-Control: no-store` header the 200 also carries is NOT asserted here -- it is
the claim of scenario 10.6 ("The feed is not stored by shared caches"), and pulling it
in would widen what this scenario validates.
"""

from dataclasses import dataclass
from typing import ClassVar, Optional

from clients.application.application_client import ApplicationClient
from clients.application.dto.project.project_list_response_dto import (
    ProjectItemDto,
    ProjectListBodyDto,
    ProjectListResponseDto,
)
from statements.account_setup import (
    NEW_DOCUMENT_CONTENT,
    NEW_DOCUMENT_STATUS,
    NEW_DOCUMENT_TITLE,
    SUPPORTED_DOCUMENT_TYPE,
    CreatedDocument,
    authenticated_access_token,
    create_document_owned_by,
)


@dataclass(frozen=True)
class TwoAccountFeeds:
    caller_document: CreatedDocument
    caller_feed: ProjectListResponseDto
    other_document: CreatedDocument
    other_feed: ProjectListResponseDto


class ProjectFeedStatements:
    # The envelope defaults an unparameterised call must apply
    # (api-specs/projects_list.yaml: page default 1, limit default 20).
    EXPECTED_PAGE: ClassVar[int] = 1
    EXPECTED_LIMIT: ClassVar[int] = 20
    # Each account holds exactly one document and nothing else, so its own feed is
    # exactly one row -- a literal, not a computed count.
    EXPECTED_TOTAL: ClassVar[int] = 1
    # projects_list.yaml: `kind` is the source table, never a status.
    DOCUMENT_KIND: ClassVar[str] = "document"
    # A document that was created and never saved has empty content, so its
    # server-derived preview is the empty string -- not a truncation of anything.
    EXPECTED_PREVIEW: ClassVar[str] = NEW_DOCUMENT_CONTENT
    # Documents are never retryable: retryable is true only for a failed generation
    # under its retry ceiling (projects_list.yaml).
    EXPECTED_RETRYABLE: ClassVar[bool] = False
    EXPECTED_TITLE: ClassVar[Optional[str]] = NEW_DOCUMENT_TITLE

    def __init__(self, client: ApplicationClient):
        self._client = client

    async def given_two_accounts_each_holding_one_document_request_their_feeds(
        self,
    ) -> TwoAccountFeeds:
        caller_token = await authenticated_access_token(self._client)
        caller_document = await create_document_owned_by(self._client, caller_token)
        other_token = await authenticated_access_token(self._client)
        other_document = await create_document_owned_by(self._client, other_token)

        return TwoAccountFeeds(
            caller_document=caller_document,
            caller_feed=await self._client.list_projects(caller_token),
            other_document=other_document,
            other_feed=await self._client.list_projects(other_token),
        )

    def assert_both_feeds_served(self, feeds: TwoAccountFeeds) -> None:
        assert feeds.caller_feed.status_code == 200, (
            f"expected the caller's feed to be served with 200, got "
            f"status_code={feeds.caller_feed.status_code}, body={feeds.caller_feed.body}"
        )
        assert feeds.other_feed.status_code == 200, (
            f"expected the other account's feed to be served with 200, got "
            f"status_code={feeds.other_feed.status_code}, body={feeds.other_feed.body}"
        )

    def assert_only_own_documents_are_returned(self, feeds: TwoAccountFeeds) -> None:
        # Pinning each feed to its exact expected envelope asserts both halves at once:
        # the owner's own document is present with every field the contract declares,
        # and nothing else is in the page.
        self._assert_feed_is_exactly(
            feeds.caller_feed, feeds.caller_document, "the caller's feed"
        )
        self._assert_feed_is_exactly(
            feeds.other_feed, feeds.other_document, "the other account's feed"
        )

    def assert_the_other_accounts_document_is_absent(self, feeds: TwoAccountFeeds) -> None:
        # The scenario names absence as its own Then, so it gets its own assertion.
        # Keyed on the full `(kind, id)` pair, because projects_list.yaml says an id is
        # unique only WITHIN a kind -- an id-only check compares across id spaces.
        self._assert_key_absent(
            feeds.caller_feed,
            feeds.other_document,
            feed_described_as="the caller's feed",
            document_described_as="the other account's document",
        )
        self._assert_key_absent(
            feeds.other_feed,
            feeds.caller_document,
            feed_described_as="the other account's feed",
            document_described_as="the caller's document",
        )

    def _assert_feed_is_exactly(
        self, feed: ProjectListResponseDto, document: CreatedDocument, described_as: str
    ) -> None:
        actual = feed.parsed_body()
        expected = self._expected_feed_holding(document)
        assert actual == expected, (
            f"expected {described_as} to be exactly {expected!r}, got {actual!r}"
        )

    def _assert_key_absent(
        self,
        feed: ProjectListResponseDto,
        document: CreatedDocument,
        feed_described_as: str,
        document_described_as: str,
    ) -> None:
        foreign_key = (self.DOCUMENT_KIND, document.id)
        actual_keys = [(item.kind, item.id) for item in feed.parsed_body().items]
        assert foreign_key not in actual_keys, (
            f"expected {document_described_as} {foreign_key!r} to be absent from "
            f"{feed_described_as}, got keys={actual_keys!r}"
        )

    def _expected_feed_holding(self, document: CreatedDocument) -> ProjectListBodyDto:
        return ProjectListBodyDto(
            items=(
                ProjectItemDto(
                    kind=self.DOCUMENT_KIND,
                    id=document.id,
                    title=self.EXPECTED_TITLE,
                    preview=self.EXPECTED_PREVIEW,
                    document_type=SUPPORTED_DOCUMENT_TYPE,
                    status=NEW_DOCUMENT_STATUS,
                    retryable=self.EXPECTED_RETRYABLE,
                    created_at=document.created_at,
                    # Document.create sets updated_at to created_at, and setup never
                    # saves the document afterwards, so the two instants are the one
                    # value captured from the create response.
                    updated_at=document.created_at,
                ),
            ),
            page=self.EXPECTED_PAGE,
            limit=self.EXPECTED_LIMIT,
            total=self.EXPECTED_TOTAL,
        )
