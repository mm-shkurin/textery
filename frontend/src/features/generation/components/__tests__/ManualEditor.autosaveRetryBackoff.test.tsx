import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { MAX_AUTOSAVE_ATTEMPTS, SAVE_ERROR_MESSAGE } from '../../hooks/useDocumentSave'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  SAVED_CONTENT,
  SAVED_PLAIN,
  SAVED_VERSION,
  asParagraph,
  enterBackoffWindow,
  playOutRetrySchedule,
} from './ManualEditor.autosaveFixture'
import {
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  SAVE_ERROR_TESTID,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Vocabulary local to the "edit typed during the backoff wait" case — the shared fixture's
// SAVED/EDITED/REVISED triple names a baseline-and-revision story, and this test needs the pair to
// read as stale-vs-latest. Derived through asParagraph so the text typed and the HTML asserted on
// the wire cannot drift apart, which is the whole reason the helper exists.
const STALE_PLAIN = 'stale content'
const LATEST_PLAIN = 'updated during wait'
const STALE_CONTENT = asParagraph(STALE_PLAIN)
const LATEST_CONTENT = asParagraph(LATEST_PLAIN)

// The bounded retry contract this scenario pins: the failed autosave fires once, then re-fires on a
// capped backoff schedule up to a fixed ceiling before giving up and surfacing the banner. The exact
// total (initial attempt + retries) is the production constant MAX_AUTOSAVE_ATTEMPTS, imported so the
// contract lives in one place — playOutRetrySchedule drains a window sized so the whole schedule
// plays out inside it, making the count deterministic, not a range.

// Scenario H9.3 (autosave failures handled per kind). A TRANSIENT autosave failure — a request
// timeout or a 5xx — is the one failure kind where retrying can actually recover. This suite pins
// the retry contract: the failed autosave re-fires ITSELF on a backoff timer (no fresh edit and no
// Сохранить click needed), the backoff is scheduled rather than an immediate hammer, and the retry
// loop is BOUNDED so a server that stays down does not spin forever. playOutRetrySchedule stands in
// for "however long the capped backoff schedule needs" so the assertions do not hardcode green's
// exact per-attempt delays.

describe('ManualEditor — a transient autosave failure retries on a capped backoff (H9.3)', () => {
  useAutosaveFailureFakeTimers()

  it('re-fires a timed-out autosave on a backoff timer (not immediately) and clears the failure once it succeeds', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockRejectedValueOnce(new RequestTimeoutError())
      .mockResolvedValue({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })

    await typeAndFireAutosave(SAVED_PLAIN)

    // The first autosave fired and rejected with a timeout — exact content and version (a failed
    // save does not bump the version, so the retry re-sends the same CREATED_VERSION).
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      CREATED_VERSION,
    )

    // The retry is SCHEDULED on a timer, not fired synchronously in the reject handler — draining
    // only the microtask queue must not have produced a second attempt yet.
    await flushMicrotasks()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // Crossing the backoff window re-fires the SAME autosave with no new edit and no click.
    await playOutRetrySchedule()

    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    // The retry re-sends the identical content at the same version — not stale, not re-serialized wrong.
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      CREATED_VERSION,
    )
    // The recovered save settles clean: the failure banner is gone and the saved status shows.
    // Asserted by CLASS, not by re-reading the matched text: getByText already matched on
    // SAVED_STATUS, so `.textContent` could never disagree with it. SAVED_BADGE_CLASS is the
    // independent fact — WHICH of ManualEditorSaveStatus's mutually exclusive branches rendered.
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
  })

  it('stops retrying a persistently-failing transient autosave after a bounded number of attempts and shows the failure', async () => {
    await enterBackoffWindow()

    // Let the whole capped-backoff schedule play out. It retries automatically and gives up after
    // exactly MAX_AUTOSAVE_ATTEMPTS total attempts (initial + capped retries) — the window is sized
    // so the whole schedule fits inside it, so the count is exact, not "more than one".
    await playOutRetrySchedule()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(MAX_AUTOSAVE_ATTEMPTS)
    // ...and every attempt carried the SAME unsaved content at the SAME unbumped version. Without
    // this the count alone passes for a retry loop that re-sent stale text or a drifting version.
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      MAX_AUTOSAVE_ATTEMPTS,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      CREATED_VERSION,
    )

    // The loop is BOUNDED: a further, equally long wait produces no additional attempts — the count
    // holds at the same defined ceiling, not merely "unchanged from whatever ran".
    await playOutRetrySchedule()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(MAX_AUTOSAVE_ATTEMPTS)

    // Having given up, it surfaces the failed-save banner — the banner's whole text is the message,
    // not merely a string containing it (the icon beside it contributes no text).
    expect(screen.getByTestId(SAVE_ERROR_TESTID).textContent).toBe(SAVE_ERROR_MESSAGE)
  })

  // Premortem gap (H9.3): an edit typed during the backoff WAIT must not be silently lost. If the
  // retry re-sent the stale content captured at the failed attempt, the successful retry would mark
  // the doc "Сохранено" over text that was never sent — data loss with no banner. The retry must
  // re-serialize the editor's LATEST content at fire time.
  it('re-sends the latest content typed during the backoff wait, not the stale content from the failed attempt', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockRejectedValueOnce(new RequestTimeoutError())
      .mockResolvedValue({ status: 'saved', version: SAVED_VERSION, content: LATEST_CONTENT })

    await typeAndFireAutosave(STALE_PLAIN)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      STALE_CONTENT,
      CREATED_VERSION,
    )

    // While the backoff timer is pending, the user keeps typing — this is the gap the retry must not
    // drop. The edit lands with no save in flight to queue against; only re-serialization saves it.
    await typeIntoEditor(LATEST_PLAIN)

    // The retry fires across the window and must carry the LATEST content, at the unchanged version.
    await playOutRetrySchedule()

    // Exactly one retry: the recovered save must settle, not chain a third write off its own resolve.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      2,
      CREATED_DOCUMENT_ID,
      LATEST_CONTENT,
      CREATED_VERSION,
    )
    // Clean only over content that was actually sent — never marked saved over the lost keystrokes.
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
  })
})
