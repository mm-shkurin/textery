import { describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { useAutosaveFailureFakeTimers } from './ManualEditor.autosave.testSupport'
import { enterBackoffWindow, playOutRetrySchedule } from './ManualEditor.autosaveFixture'
import {
  discardAttemptDiagnostics,
  expectAbandonmentRecorded,
} from './ManualEditor.autosaveAbandonFixture'
import {
  RETRYING_BADGE_CLASS,
  SAVE_ERROR_TESTID,
  SAVE_STATUS_BASE_SELECTOR,
  badgeClassName,
  dispatchBeforeUnload,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Scenario H9.4 — premortem CREDIBLE #2 on 82fd240: the H9.3 backoff ladder (1s/2s/4s) opened a
// ~7-second window in which a save that has ALREADY failed is indistinguishable, to the user, from
// one still on its first round trip. `useDocumentSave.performSave` deliberately holds
// isSavingRef/setIsSaving(true) across the whole gap and withholds the banner until attempt 4
// spends, so the only thing the UI moves during those seconds is the «Сохранить» spinner — which
// said exactly the same thing one millisecond before attempt 1 was rejected.
//
// Every existing retry suite drains the schedule with playOutRetrySchedule() and asserts only the
// TERMINAL state, so nothing in the suite observes the interior of the window at all. These two
// cases are that missing observation, from the two directions that matter:
//
//   1. the window is entered and the user stays in the editor — the status badge must say a save
//      attempt failed and is being retried, not merely repeat the pre-save «черновик».
//   2. the window is entered and the editor UNMOUNTS (in-app back — `flow.backFromEditor` just
//      unmounts; it is NOT beforeunload, which ManualEditor.tsx:127-138 guards alone). The
//      []-scoped cleanup at useDocumentSave.ts:76-81 clears the pending backoff timer, so the
//      retry never fires and the write is dropped. Nothing anywhere records that it was dropped:
//      the one console.error in the .catch belongs to the earlier attempt, not to the abandonment.

// The badge branch this scenario demands is RETRYING_BADGE_CLASS. ManualEditorSaveStatus renders
// three mutually exclusive modifiers today (--dirty / --saved / --failed) and none of them means
// "attempt failed, retrying". Asserted as a CLASS on the badge's stable base element rather than as
// text so GREEN owns the wording: the fact under test is WHICH branch rendered, not what it spells.

describe('ManualEditor — the interior of the autosave backoff window (H9.4)', () => {
  useAutosaveFailureFakeTimers()

  // RED 2026-07-29: fails at the badge className assertion —
  // "expected 'me-save-status me-save-status--dirty' to be 'me-save-status
  // me-save-status--retrying'". ManualEditorSaveStatus has no retrying branch; the badge inside the
  // window is byte-identical to the badge before any save was attempted.
  it('tells the user a save attempt failed while the backoff ladder is still running', async () => {
    // Provably INSIDE the window, not past it — enterBackoffWindow asserts attempt 1 fired, rejected,
    // and carried the user's edit at the document's current OCC version. The absent banner is the
    // other half: the ladder has not spent its remaining attempts, so this really is the interior.
    const { container } = await enterBackoffWindow()
    expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()

    // And the document is genuinely unsaved at this instant — the browser guard is armed, which is
    // the independent confirmation that the app itself considers this state unpersisted.
    expect(dispatchBeforeUnload()).toBe(true)

    // The whole point: knowing the work is unsaved is NOT the same as knowing a save was attempted
    // and rejected. --dirty is what the badge read before any save was ever tried, so re-rendering
    // it here tells the user nothing has changed while the app quietly burns seven seconds.
    //
    // Asserted as the EXACT className — base class plus exactly one modifier — rather than as
    // toHaveClass(RETRYING_BADGE_CLASS). toHaveClass still passes when the element carries --retrying
    // AND --dirty, which is precisely how a GREEN bolts a new branch on beside the old one instead of
    // replacing it, leaving the badge styled by whichever CSS rule wins. One strict fact here proves
    // existence, proves the retrying branch rendered, and proves the other three did not.
    const badge = container.querySelector(SAVE_STATUS_BASE_SELECTOR)
    expect(badge?.className).toBe(badgeClassName(RETRYING_BADGE_CLASS))
  })

  // RED 2026-07-29: fails inside expectAbandonmentRecorded(), at
  // `expect(console.error).toHaveBeenCalledTimes(1)` —
  // "AssertionError: expected \"error\" to be called 1 times, but got 0 times". The []-scoped
  // cleanup clears the retry timer and returns; the abandoned write leaves no trace at all.
  it('records that the write never landed when the editor unmounts mid-backoff', async () => {
    const { unmount } = await enterBackoffWindow()

    // The edit is provably unpersisted at the instant we are about to walk away from it: the app's
    // own browser guard is armed. This is what makes the abandonment below matter — without it the
    // test would be proving a retry was dropped without establishing there was anything to lose.
    expect(dispatchBeforeUnload()).toBe(true)

    // Drop the rejection's own console.error on the floor: it is attempt 1's diagnostic and says
    // nothing about abandonment. Everything asserted after this line is caused by the unmount.
    discardAttemptDiagnostics()

    // In-app back. The user never leaves the page, so the beforeunload guard armed above is never
    // reached — and the []-scoped cleanup clears the pending retry timer on the way out.
    unmount()
    await playOutRetrySchedule()

    // The write really is gone: the ladder had attempts left, and none of them fired.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // So the abandonment must be recorded exactly once, through the app's only sink. Without this
    // the user's last edit vanishes with no trace in the running system anywhere.
    expectAbandonmentRecorded()
  })
})
