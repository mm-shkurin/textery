import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'
import { isTransientFailure } from '../../hooks/autosaveRetryPolicy'
import * as documentApi from '../../api/documentApi'
import {
  crossDebounceBoundary,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  CREATED_DOCUMENT_ID,
  renderCreatedDocument,
} from './ManualEditor.autosaveRender.testSupport'
import {
  RETRY_VERSION,
  REVISED_CONTENT,
  REVISED_PLAIN,
  SAVED_CONTENT,
  SAVED_PLAIN,
  SAVED_VERSION,
  echoSavedAtRetryVersion,
  playOutRetrySchedule,
  saveBaselineThenTransientFailure,
} from './ManualEditor.autosaveFixture'
import {
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  SAVE_ERROR_TESTID,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4 — the fire-time suppression is scoped to failures that PROVABLY did not land.
//
// A RequestTimeoutError is not one of them. It is a purely CLIENT-side deadline: httpClient races
// the request against its own timer and rejects when the timer wins, whether or not the transport
// ever aborted and whether or not the server went on to commit the write. So after a timeout the
// server's content is UNKNOWN — and the guard's memory of "the server holds SAVED_CONTENT", recorded
// before the timed-out PUT was ever sent, is exactly the thing the timeout put in doubt.
//
// Suppressing the retry against that memory is how the editor and the server silently diverge:
//   1. save #1 confirms SAVED_CONTENT (v8) — the guard remembers it.
//   2. the user edits to EDITED_CONTENT; the PUT times out client-side but the SERVER APPLIES IT.
//   3. the user undoes back to SAVED_CONTENT inside the backoff window.
//   4. the retry fires, sees current === remembered, settles clean and writes NOTHING.
// The editor shows the revert, the server holds the edit, the badge reads «Сохранено», beforeunload
// stands down, and «Сохранить» routes into the same suppression — so there is no way left to force
// the revert through short of making a throwaway edit. The revert is silently lost.
//
// The same principle the cycle already applies to settleFailed ("a failure leaves the server state
// unknown, so the memory must not outlive it") has to reach the retry gate three lines above it: a
// timeout must forget, and the retry must issue a real PUT carrying the reverted content — which
// converges through saveDocument's own 409 refetch-and-retry when the timed-out write did land.
//
// THESE ASSERTIONS ARE DELIBERATELY INSUFFICIENT ALONE. Every one of them also passes under an
// implementation that simply never suppresses — delete the fire-time isAlreadySaved gate entirely
// and this suite stays green, because "always write" satisfies "write here" too. What makes the
// pair a specification is the INVERSE assertion in the sibling suite
// ManualEditor.autosaveDirtyGuardBackoffRevert.test.tsx, whose 503 suppression count
// (`toHaveBeenCalledTimes(2)`) is the only component-level discriminator that fails on an
// always-retry implementation.
// Weakening, re-scoping, or .skip-ing that count removes this suite's sole discriminator. The axis
// the two of them straddle is pinned directly, without either component fixture, in
// hooks/__tests__/autosaveRetryPolicy.mayHaveLandedServerSide.test.ts.
describe('ManualEditor — a revert after a TIMED-OUT save is still written (H9.4)', () => {
  useAutosaveFailureFakeTimers()

  it('retries with the reverted content because a timeout leaves the server state unknown', async () => {
    // The scenario presupposes a timeout is retried at all rather than surfacing a banner outright.
    expect(isTransientFailure(new RequestTimeoutError())).toBe(true)

    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument)
      .mockResolvedValueOnce({ status: 'saved', version: SAVED_VERSION, content: SAVED_CONTENT })
      // The client gave up waiting. Nothing here says the server did not commit EDITED_CONTENT —
      // that is precisely the point.
      .mockRejectedValueOnce(new RequestTimeoutError())
      .mockImplementation(echoSavedAtRetryVersion)

    // Baseline save (the guard now remembers SAVED_CONTENT as confirmed by the server), then edit #2
    // which TIMES OUT. Transient, so a backoff timer is pending and the cycle stays "in flight" —
    // but unlike the sibling's 503 the server may well have committed it.
    await saveBaselineThenTransientFailure()

    // The undo lands INSIDE the backoff window, so it can only queue.
    await typeIntoEditor(SAVED_PLAIN)
    expect(dispatchBeforeUnload()).toBe(true)

    await playOutRetrySchedule()

    // The retry must actually write. Anything the timed-out PUT may have left on the server is
    // overwritten by the content the user can see.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      3,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      SAVED_VERSION,
    )
    // And it converges: one real write settles the document, it does not chain a fourth.
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
    expect(dispatchBeforeUnload()).toBe(false)

    // The retry's own RESULT was adopted, not discarded — the next edit goes out at the version the
    // retry returned. A green that fires the PUT but drops the response leaves the document at
    // SAVED_VERSION and every assertion above still passes; this tuple is what catches it. The
    // re-arm also gives the `false` three lines up something to mean: ManualEditor registers the
    // beforeunload listener only while dirty, so `false` alone is equally the answer when no guard
    // was ever installed.
    await typeIntoEditor(REVISED_PLAIN)
    expect(dispatchBeforeUnload()).toBe(true)
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(4)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      4,
      CREATED_DOCUMENT_ID,
      REVISED_CONTENT,
      RETRY_VERSION,
    )
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(dispatchBeforeUnload()).toBe(false)
  })
})
