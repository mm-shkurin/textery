from datetime import UTC, datetime, timedelta
from uuid import UUID

from document.document import Document
from project.project_item import ProjectItem
from project.project_page import ProjectPage

# The seeded document's values, stated here rather than read back off the entity
# the test itself built. `document.status` as an expectation is a mirror: it echoes
# the domain's own hardcoded default, so both sides of the equality move together
# and the feed's projection of that column is never actually pinned.
SEEDED_DOCUMENT_TYPE = "эссе"

# NOT seeded, and cannot be: `Document.create` and `Document.create_from_generation`
# both refuse a `status` parameter by design (mass-assignment guard) and hardcode
# `DRAFT_STATUS`. This literal is therefore the only status a seeded document can
# have, hand-written on purpose. Importing `DRAFT_STATUS` here to "remove the
# duplication" would recreate exactly the mirror this file avoids: the expectation
# and the value under test would become one symbol, and a projection emitting a
# constant instead of reading `documents.status` would stay green.
EXPECTED_STATUS_OF_ANY_SEEDED_DOCUMENT = "draft"

# The one expected field this test structurally CANNOT pin, recorded rather than
# left to look pinned. `retryable` has no `documents` column to be read from -- a
# document is never retryable, only a failed generation is -- so the projection's
# only correct implementation is the literal `False`, which is also exactly what
# the current id-only placeholder emits. Every other field here fails the red
# against that placeholder; this one would pass it. It is not repairable by
# seeding, and inventing a column to make it bite would ship schema under no
# contract. The field first discriminates on the generations arm (1.2/1.3), where
# a failed row must come back `retryable=True` -- that is where it gets a test
# that can fail.
EXPECTED_RETRYABLE_OF_ANY_DOCUMENT_ROW = False

SEEDED_CREATED_AT = datetime(2026, 3, 1, 9, 15, 0, tzinfo=UTC)
# Deliberately NOT equal to SEEDED_CREATED_AT -- 37 minutes later. Both factories
# set `updated_at=created_at`, so a projection that emitted the created column
# twice would satisfy a same-instant expectation and never be caught. Two distinct
# instants make the two columns tell each other apart.
#
# Stated as a literal rather than as `SEEDED_CREATED_AT + timedelta(minutes=37)`:
# an expected value the test computes is a value the test can compute wrongly, and
# the arithmetic form also prints the two instants as one derived chain in a
# failure diff instead of two independent constants the reader can compare.
SEEDED_UPDATED_AT = datetime(2026, 3, 1, 9, 52, 0, tzinfo=UTC)

# Short and plain on purpose. 1.1 owes only that `preview` is READ from
# `documents.content` -- for content this short and this free of markup, the
# preview is the content verbatim. The grapheme-aware 200-code-point trim is
# scenario 6.2's claim and the HTML strip is 6.3's; seeding long or marked-up
# content here would smuggle their derivation under 1.1's name and leave this test
# asserting a behaviour no one has specified yet.
SEEDED_TITLE = "Весна в городе"
SEEDED_CONTENT = "Короткий текст."

# The envelope a default (unparameterised) feed request owes for one seeded row.
# Named rather than inlined so that a change to the domain's default page size is
# a change to one constant here and not to a bare 20 in an assertion.
EXPECTED_FIRST_PAGE = 1
EXPECTED_DEFAULT_LIMIT = 20
EXPECTED_TOTAL_FOR_ONE_SEEDED_DOCUMENT = 1

_ROW_CARRIES_THE_CONTRACT_FIELDS = (
    "every ProjectItem field must be projected from the document row -- kind, "
    "title, preview, document_type, status, retryable and both timestamps"
)

_TITLED_ROW_CARRIES_THE_STORED_TEXT = (
    "title and preview must be READ from documents.title and documents.content, "
    "not emitted as literals: a document seeded with a non-NULL title and "
    "non-empty content must surface both"
)

# Says what whole-page equality buys TODAY. It must not promise checks on `page`,
# `limit` and `total`: those belong to the same contract but are not yet fields of
# `ProjectPage`, and naming them in a failure message tells the next reader this
# assertion covers ground it does not. They arrive with the paging scenarios that
# assert them, and this equality widens to cover them for free on the day they do.
_PAGE_HOLDS_EXACTLY_THE_EXPECTED_ROW = (
    "the whole ProjectPage must equal the expectation, not merely contain a "
    "matching row: an assertion that reaches past the page into `items` -- or "
    "that checks only items[0] -- keeps passing while the feed serves an extra, "
    "a missing or a duplicated row"
)

_TIMESTAMPS_CARRY_AN_OFFSET = (
    "both feed timestamps must stay tz-aware: the contract serializes UTC "
    "ISO-8601 with an explicit offset, and a naive datetime cannot"
)

_TIMESTAMPS_ARE_THE_STORED_INSTANTS = (
    "the row's timestamps must be the document's own, not a placeholder instant"
)


def _expected_page(document_id: UUID, title: str | None, preview: str) -> ProjectPage:
    """The whole page the feed owes for one seeded document.

    Built here in the test tree, never imported from
    `access.project.project_feed_storage`: importing the module's own row factory
    is what had collapsed the previous expectation into `document.id == row_id`,
    with both sides of the equality one code path.

    Takes the id rather than the entity to keep that separation visible in the
    signature: identity is the only thing this expectation may draw from the
    object the test built, and every other field is stated as a literal above. An
    entity parameter would leave the door open to reading a second field off it
    later and quietly restoring the mirror.
    """
    return ProjectPage(
        items=(
            ProjectItem(
                kind="document",
                id=document_id,
                title=title,
                preview=preview,
                document_type=SEEDED_DOCUMENT_TYPE,
                status=EXPECTED_STATUS_OF_ANY_SEEDED_DOCUMENT,
                retryable=EXPECTED_RETRYABLE_OF_ANY_DOCUMENT_ROW,
                created_at=SEEDED_CREATED_AT,
                updated_at=SEEDED_UPDATED_AT,
            ),
        ),
        # Stated, not defaulted. The page-level counters are part of what the feed
        # owes, and leaving them to `ProjectPage`'s defaults would let a repository
        # that returned `total=0` beside a one-row page pass this assertion -- the
        # exact shape a client uses to decide there is no page 2.
        page=EXPECTED_FIRST_PAGE,
        limit=EXPECTED_DEFAULT_LIMIT,
        total=EXPECTED_TOTAL_FOR_ONE_SEEDED_DOCUMENT,
    )


class ProjectFeedRowExpectations:
    """The row-level half of the feed storage DSL, mixed into the Statements class.

    Split out only for the 200-line limit; it holds no state and reads nothing the
    seeding half owns.
    """

    def assert_row_is_projected_from(self, page: ProjectPage, document: Document) -> None:
        """An untitled, empty-content document's row -- as a whole page.

        `title` stays **None**: neither factory sets one on the manual path, the
        contract declares `title` nullable and omits it from `required`, and
        coercing NULL to `''` would destroy the null/blank distinction scenario
        3.3's `title_asc` ordering depends on. `preview` is `''` because the
        content is -- this case alone cannot pin that the column is read at all,
        which is why `assert_titled_row_is_projected_from` exists.
        """
        assert page == _expected_page(document.id, title=None, preview=""), (
            f"{_ROW_CARRIES_THE_CONTRACT_FIELDS}; {_PAGE_HOLDS_EXACTLY_THE_EXPECTED_ROW}"
        )

    def assert_titled_row_is_projected_from(self, page: ProjectPage, document: Document) -> None:
        """A document that actually carries a title and content -- as a whole page.

        This is the case the empty-content one structurally cannot make: there,
        the expected `title=None` and `preview=''` are equal to the values a
        projection would emit if it never selected the two columns, so the
        assertion passed against a literal. Here the seeded values are neither
        NULL nor empty, so only a SELECT that reads `documents.title` and
        `documents.content` can satisfy it.
        """
        assert page == _expected_page(document.id, title=SEEDED_TITLE, preview=SEEDED_CONTENT), (
            f"{_TITLED_ROW_CARRIES_THE_STORED_TEXT}; {_PAGE_HOLDS_EXACTLY_THE_EXPECTED_ROW}"
        )

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
