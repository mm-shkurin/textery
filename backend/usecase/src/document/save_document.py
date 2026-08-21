from uuid import UUID

from analytics.analytics_recorder import AnalyticsRecorder, NullAnalyticsRecorder
from analytics.event_names import DOCUMENT_SAVED
from document.document import Document
from document.document_content import MAX_CONTENT_LENGTH, DocumentContent
from document.document_repository import DocumentRepository
from document.html_sanitizer import HtmlSanitizer
from document.title_update import TitleUpdate
from shared import error_codes
from shared.clock import Clock
from shared.exceptions import ConflictException, NotFoundException, ValidationException
from shared.unit_of_work import NullUnitOfWork, UnitOfWork

MIN_VERSION = 1


class SaveDocument:
    """Save the full editor content, guarded by the version token."""

    # Interpolated from the constant that owns the rule. Spelled out, the message
    # keeps quoting the old number when the cap moves -- a lie nothing checks, told
    # only to the user who hit the limit.
    CONTENT_TOO_LONG_MESSAGE = (
        f"The content exceeds the maximum length of {MAX_CONTENT_LENGTH} characters."
    )
    INVALID_VERSION_MESSAGE = "The version must be a positive integer."

    def __init__(
        self,
        document_repository: DocumentRepository,
        html_sanitizer: HtmlSanitizer,
        clock: Clock,
        unit_of_work: UnitOfWork | None = None,
        analytics_recorder: AnalyticsRecorder | None = None,
    ) -> None:
        self.document_repository = document_repository
        self.html_sanitizer = html_sanitizer
        self.clock = clock
        self.unit_of_work = unit_of_work or NullUnitOfWork()
        # Null by default, fail-open at use: a save that persisted must answer
        # 200 whatever analytics does.
        self._analytics_recorder = analytics_recorder or NullAnalyticsRecorder()

    async def execute(
        self,
        document_id: UUID,
        owner_id: UUID,
        content: str,
        version: int,
        # `str` is TRANSITIONAL and owned by adapters-discovery (a): the PUT route
        # still hands the raw Pydantic field over, and only there can absent be
        # told from an explicit null (`model_fields_set`). Until it maps the wire
        # shape to a TitleUpdate itself, a raw string is read as "set this title".
        title: TitleUpdate | str | None = None,
    ) -> Document:
        self._validate_version(version)
        sanitized = self.html_sanitizer.sanitize(self._validate_content(content))

        saved = await self.document_repository.save_content_if_version_matches(
            document_id=document_id,
            owner_id=owner_id,
            content=sanitized,
            expected_version=version,
            updated_at=self.clock.now(),
            title=self._title_intent(title),
        )
        if saved is None:
            # A save that persisted NOTHING records nothing (§9.7): the miss
            # branch either raises or resolves an idempotent replay, and neither
            # is a save the funnel should count.
            return await self._explain_miss(document_id, owner_id, sanitized, version)
        await self.unit_of_work.commit()
        # After the commit, never before: an event recorded first and a commit
        # that then failed is a save in the data that never happened (§12.4).
        await self._analytics_recorder.record(
            event_name=DOCUMENT_SAVED, visitor_id=None, user_id=owner_id
        )
        return saved

    @staticmethod
    def _title_intent(title: TitleUpdate | str | None) -> TitleUpdate:
        """Turn what the caller passed into a named intent.

        `None` here means ABSENT ONLY -- the `title` argument was not supplied.
        It must NEVER be how an adapter spells an explicit wire `"title": null`:
        only the route can tell absent from null (`model_fields_set`), and if it
        forwards `None` for a null the erasure is silently converted into a
        preserve and the whole clear path no-ops with every test green. A route
        that means "clear" passes `TitleUpdate.clear()`.

        Absence is spelled `preserve()` rather than forwarded as a bare `None`:
        the port declares `None` unusable for intent, and the absent case is the
        most-travelled path of all, so it must not be the one still carrying the
        ambiguous value.

        Blankness is NOT decided here. `TitleUpdate.__post_init__` folds a blank
        string down to preserve on every construction path -- including the
        constructor -- so re-testing it here could only ever be a guard that
        cannot fire. The invariant lives on the type.
        """
        if title is None:
            return TitleUpdate.preserve()
        return TitleUpdate.of(title) if isinstance(title, str) else title

    def _validate_version(self, version: int) -> None:
        # bool is an int subclass in Python, and `True == 1`, so a JSON `true` would
        # sail through a bare isinstance(version, int) check and act as version 1.
        if isinstance(version, bool) or not isinstance(version, int) or version < MIN_VERSION:
            raise ValidationException(
                error_code=error_codes.INVALID_VERSION, message=self.INVALID_VERSION_MESSAGE
            )

    def _validate_content(self, content: str) -> str:
        """The content, proven within the cap and NFC-normalized.

        Called BEFORE sanitizing: sanitizing first would make the parser chew
        through an adversarial payload before we decline it, and the cap is a
        contract about what the client sent, not about what survived cleaning.
        DocumentContent caps the raw string, NFC-normalizes, then re-caps.
        """
        try:
            return DocumentContent(content).value
        except ValueError as error:
            raise ValidationException(
                error_code=error_codes.CONTENT_TOO_LONG, message=self.CONTENT_TOO_LONG_MESSAGE
            ) from error

    async def _explain_miss(
        self, document_id: UUID, owner_id: UUID, sanitized: str, version: int
    ) -> Document:
        """The CAS matched nothing. Work out which of the three reasons it was.

        The re-read is what lets scenario 6.2 answer 200: a client whose save
        already landed and retried would otherwise get a 409 and be sent into a
        refetch loop over a write that succeeded.

        The replay rule is deliberately narrow -- the stored content must equal
        ours AND the version must be exactly ours + 1. A `content -> other ->
        content` history therefore still conflicts, and (per the amended scenario
        6.7) two concurrent saves carrying *different* content cannot both pass:
        the loser's content will not match what landed.
        """
        current = await self.document_repository.find_by_id_and_owner(document_id, owner_id)
        if current is None:
            # Absent and foreign are one answer, always. A distinct response for
            # "exists but not yours" would confirm the id -- and a 409 here would
            # additionally confirm the version guess was right.
            raise NotFoundException(f"document {document_id} not found")
        if current.content == sanitized and current.version == version + 1:
            return current
        raise ConflictException(f"document {document_id} was modified concurrently")
