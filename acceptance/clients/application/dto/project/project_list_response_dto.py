"""Typed parse of `GET /api/v1/projects` (api-specs/projects_list.yaml).

The envelope is parsed into frozen dataclasses instead of being asserted key-by-key on
a raw dict. Two reasons, both about strictness rather than tidiness: frozen dataclasses
compare deeply, so a single equality pins every contract field at once; and required
keys are read by subscript, so a response that omits one raises at parse time instead
of reading as `None` and quietly satisfying a `.get()`-based assertion.

`ProjectListResponseDto` deliberately keeps the raw `body` and parses only on demand --
during RED the endpoint answers Starlette's route-miss 404, and parsing that eagerly
would raise a KeyError before the status-code assertion could report the real failure.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


def parse_feed_timestamp(raw: str) -> datetime:
    """Parse a feed timestamp, enforcing the contract's explicit-offset requirement.

    projects_list.yaml: "UTC ISO-8601 with explicit offset". A naive string would
    compare equal to the right instant while dropping the offset the client needs to
    sort two rows created either side of local midnight -- so offset-explicitness is
    asserted here, at the parse, and the value is normalized to UTC for comparison.
    """
    parsed = datetime.fromisoformat(raw)
    assert parsed.tzinfo is not None, (
        f"expected a feed timestamp carrying an explicit UTC offset, got naive {raw!r}"
    )
    assert parsed.utcoffset() == timedelta(0), (
        f"expected a feed timestamp expressed in UTC (offset +00:00), got {raw!r} "
        f"with offset={parsed.utcoffset()}"
    )
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ProjectItemDto:
    """One feed row -- every field ProjectItem declares, none of them optional to assert."""

    kind: str
    id: str
    title: Optional[str]
    preview: str
    document_type: str
    status: str
    retryable: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_json(cls, item: dict) -> "ProjectItemDto":
        retryable = item["retryable"]
        # `False == 0` in Python, so a JSON number would satisfy a plain equality
        # against False. The contract says boolean; pin the type at the parse.
        assert isinstance(retryable, bool), (
            f"expected `retryable` to be a JSON boolean, got {retryable!r} "
            f"({type(retryable).__name__})"
        )
        return cls(
            kind=item["kind"],
            id=item["id"],
            # `title` is the only non-required field on ProjectItem and is nullable:
            # absent and null both mean "untitled". `.get` is the contract's own shape
            # here, not a defensive fallback -- every other key is subscripted.
            title=item.get("title"),
            preview=item["preview"],
            document_type=item["document_type"],
            status=item["status"],
            retryable=retryable,
            created_at=parse_feed_timestamp(item["created_at"]),
            updated_at=parse_feed_timestamp(item["updated_at"]),
        )


@dataclass(frozen=True)
class ProjectListBodyDto:
    """The `ProjectListResponse` envelope: items plus the three paging counters."""

    items: tuple[ProjectItemDto, ...]
    page: int
    limit: int
    total: int

    @classmethod
    def from_json(cls, body: dict) -> "ProjectListBodyDto":
        return cls(
            items=tuple(ProjectItemDto.from_json(item) for item in body["items"]),
            page=body["page"],
            limit=body["limit"],
            total=body["total"],
        )


@dataclass(frozen=True)
class ProjectListResponseDto:
    status_code: int
    body: Optional[dict]

    def parsed_body(self) -> ProjectListBodyDto:
        assert self.body is not None, (
            f"expected the feed to answer a JSON envelope, got no parseable body "
            f"(status_code={self.status_code})"
        )
        return ProjectListBodyDto.from_json(self.body)
