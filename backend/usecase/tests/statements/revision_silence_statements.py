import logging

from document_edit.revision_scope import RevisionScope

from fake.document_edit.fake_ai_edit_repository import (
    FailingDocumentScopeRepository,
    StorageUnavailableError,
)
from statements.arranged import arranged
from statements.log_recorder import RecordingLogger
from statements.revision_guard_base import (
    RECORDED_REVISION_ID,
    RECORDED_REVISION_NUMBER,
    RevisionGuardBase,
)
from statements.revision_refusal_log_statements import GUARD_LOGGER_NAME

# Qualified by class: `RevisionOutageStatements` pins a deliberately *different*
# outage text, and two same-named constants that must stay different are the drift
# trap the scope-field lists in this family already closed by qualifying their names.
SILENCE_OUTAGE_MESSAGE = "the store is down"

SUCCESS_PATH = "the successful resolution"
DOCUMENT_OUTAGE_PATH = "the document-store outage"
REVISION_OUTAGE_PATH = "the revision-store outage"


class RevisionSilenceStatements(RevisionGuardBase):
    """Everything that is not a refusal must leave the refusal channel empty.

    The causes are only usable as an operability signal if a spike in them means
    probing rather than traffic. Two paths can spoil that, and they spoil it in
    opposite directions: a success that logs makes the channel pure noise, and an
    outage that logs makes a database falling over read as a probing campaign in
    the one channel built to attribute probes -- while the caller, on that same
    implementation, would be getting the canonical 404 that hides the incident.
    """

    def __init__(self) -> None:
        super().__init__()
        self._recorder = RecordingLogger(GUARD_LOGGER_NAME)
        self._quiet: dict[str, list[logging.LogRecord]] = {}
        self._outages: dict[str, object] = {}
        self._resolved_scope: RevisionScope | None = None

    def given_the_guards_own_log_is_collected(self) -> None:
        self._recorder.start()

    def stop_collecting(self) -> None:
        self._recorder.stop()

    async def request_the_revision_under_its_own_document(self) -> None:
        self._recorder.clear()
        self._resolved_scope = await self.resolve(self.first_document_id)
        self._quiet[SUCCESS_PATH] = self._recorder.taken()

    async def request_the_revision_while_either_store_is_down(self) -> None:
        """Both outage paths in one act step, in the only order that works.

        The revision store may only be armed to fail *after* the document-store
        path has run, or the first request would fail for two reasons at once.
        That is a mechanical ordering constraint, and it used to sit in the test
        body as a `given` wedged between two `when`s -- the one place a reader
        cannot tell a scenario fact from a wiring detail.
        """
        await self._request_with_the_document_store_down()
        self.revision_repository.fail_every_lookup_with(
            StorageUnavailableError(SILENCE_OUTAGE_MESSAGE)
        )
        await self._request_with_the_revision_store_down()

    async def _request_with_the_revision_store_down(self) -> None:
        self._recorder.clear()
        self._outages[REVISION_OUTAGE_PATH] = await self._outcome_of(
            self.resolve(self.first_document_id)
        )
        self._quiet[REVISION_OUTAGE_PATH] = self._recorder.taken()

    async def _request_with_the_document_store_down(self) -> None:
        self._recorder.clear()
        failing = FailingDocumentScopeRepository(StorageUnavailableError(SILENCE_OUTAGE_MESSAGE))
        self._outages[DOCUMENT_OUTAGE_PATH] = await self._outcome_of(
            self.resolve_via(failing, self.first_document_id)
        )
        self._quiet[DOCUMENT_OUTAGE_PATH] = self._recorder.taken()

    async def _outcome_of(self, resolution) -> object:
        """Records what came back; judges none of it.

        This used to swallow `StorageUnavailableError` and raise `AssertionError`
        on anything else, which enforced a real behavioural contract -- the outage
        reached the caller -- invisibly, from inside an act step, where no reader
        of the test body could see it. It is now
        `assert_each_outage_reached_the_caller`, in the then-phase where it shows.
        """
        try:
            return await resolution
        except Exception as raised:  # noqa: BLE001 -- the then-phase pins the exact type
            return raised

    def assert_the_revision_actually_resolved(self) -> None:
        """Silence is only the right answer if the request succeeded.

        The mirror of `assert_each_outage_reached_the_caller`, and it was missing:
        the test is named "when the revision resolves", but nothing established
        that it did. A guard that returned `None`, refused, or handed back another
        document's row is silent too, and would satisfy the emptiness assertion
        perfectly -- turning the positive control into a second negative one.
        """
        scope = arranged(self._resolved_scope, "resolved_scope")
        expected = RevisionScope(
            id=RECORDED_REVISION_ID,
            revision_number=RECORDED_REVISION_NUMBER,
            document_id=self.first_document_id,
        )
        assert scope == expected, (
            f"the success path returned {scope}, expected {expected} -- an empty refusal "
            f"channel only means the happy path is silent if the happy path happened"
        )

    def assert_the_successful_resolution_was_silent(self) -> None:
        self._assert_silence_on((SUCCESS_PATH,))

    def assert_both_outages_were_silent(self) -> None:
        self._assert_silence_on((DOCUMENT_OUTAGE_PATH, REVISION_OUTAGE_PATH))

    def _assert_silence_on(self, expected_paths: tuple[str, ...]) -> None:
        """The roster of exercised paths is pinned before it is walked.

        Looping over whatever `_quiet` happens to hold makes the assertion agree
        with any subset of the paths, including a single one: dropping one of the
        two outage requests would leave the remaining emptiness check passing and
        the missing path unnoticed.
        """
        assert tuple(self._quiet) == expected_paths, (
            f"the paths exercised were {tuple(self._quiet)}, expected {expected_paths} -- a "
            f"roster read back off the act steps agrees with any subset of itself"
        )
        # Indexed out of the pinned tuple, not walked as `self._quiet.items()`: a loop
        # over what the act steps recorded agrees with any subset of them, and leaves
        # the roster equality above as the only thing between a skipped path and green.
        for which in expected_paths:
            records = self._quiet[which]
            assert records == [], (
                f"{which} emitted {[record.getMessage() for record in records]} on "
                f"'{GUARD_LOGGER_NAME}' -- the refusal causes are only trustworthy as an "
                f"operability signal if nothing but a refusal produces them"
            )

    def assert_each_outage_reached_the_caller(self) -> None:
        """Silence is only the right answer if the outage itself propagated.

        Without this, an implementation that rendered the outage as the canonical
        404 -- the exact defect `RevisionOutageStatements` owns -- would satisfy
        every emptiness assertion above, because a 404 that logs nothing is silent
        too. Kept here rather than delegated because it is the precondition that
        makes this class's own subject meaningful.
        """
        expected_paths = (DOCUMENT_OUTAGE_PATH, REVISION_OUTAGE_PATH)
        assert tuple(self._outages) == expected_paths, (
            f"the outage paths exercised were {tuple(self._outages)}, expected {expected_paths}"
        )
        for which in expected_paths:
            outcome = self._outages[which]
            actual = (type(outcome), str(outcome))
            assert actual == (StorageUnavailableError, SILENCE_OUTAGE_MESSAGE), (
                f"{which} surfaced as {type(outcome).__name__}('{outcome}'), expected "
                f"StorageUnavailableError('{SILENCE_OUTAGE_MESSAGE}') to propagate out of the "
                f"guard -- an outage rendered as the canonical 404 is silent too, so the "
                f"emptiness assertions alone cannot tell the two apart"
            )
