import { describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  AUTOSAVE_DEBOUNCE_MS,
  crossDebounceBoundary,
  editorContentHtml,
  flushMicrotasks,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFailureFakeTimers,
} from './ManualEditor.autosave.testSupport'
import {
  EDITED_PLAIN,
  SAVED_CONTENT,
  SAVED_PLAIN,
  armServerConfirmsSavedContent,
  expectBaselineSaveOnWire,
  expectNoAbandonmentRecorded,
} from './ManualEditor.autosaveFixture'
import {
  dispatchBeforeUnload,
  expectOnlyDirtyBadge,
  expectOnlySavedBadge,
  expectSavedBadge,
} from './ManualEditor.saveStatus.testSupport'

vi.mock('../../api/documentApi')

// Where inside the debounce window case (b)'s manual click lands. Derived from the production constant
// rather than written as a bare number: the click has to land strictly INSIDE the window, and retuning
// the debounce must not leave this case clicking after a deadline that has already passed — which
// would quietly turn it into a different test. Deliberately NOT shared with
// ManualEditor.manualSaveTrailingAutosave.test.tsx's own click offset: that suite pins a different
// instant, and collapsing two independent "somewhere inside the window" choices into one constant
// would couple two cases that have no reason to move together.
const CLICK_AT_MS = AUTOSAVE_DEBOUNCE_MS / 2

// Scenario H9.4 — the two ways the abandonment record fires over a document the server already has.
// Found by agent-review CONCERNS #1 + premortem CREDIBLE #1 on both `264fab2` and `f24de68`.
//
// `hasPendingEditRef` (armed in useAutosave's returned scheduler, read by useAbandonedSaveRecord's
// []-scoped cleanup) models exactly one fact: «a debounce timer is armed». It is cleared in ONE
// place — inside the timer callback, i.e. only when the timer actually fires. So wherever the armed
// write is made MOOT without the timer firing, the flag stays true over nothing, and backing out
// before the deadline writes a false record into the app's only diagnostic sink.
//
// The existing twins cannot see either case. The settled-write twin drives `typeAndFireAutosave`,
// which lets the timer fire — the one path that DOES clear the flag. The untouched-document twin
// never sets it (`vi.getTimerCount()).toBe(0)`). Both cases below unmount with the timer still
// armed, which is the window neither twin visits.
//
// Both are ordinary: no 5xx, no race, no second tab. A keystroke and an undo; a keystroke and a
// click. That is how the one record that means something drowns.
describe('ManualEditor — no abandonment record when the armed write had nothing left to write (H9.4)', () => {
  useAutosaveFailureFakeTimers()

  // (a) Revert-to-saved inside the gap. The user-facing motions are Ctrl+Z, a Backspace of the one new
  // character, bold-then-unbold — this case drives NONE of them: `typeIntoEditor` assigns textContent
  // and fires `input`, so what is pinned is the shared consequence (a transaction restoring the saved
  // bytes), not Tiptap's history or mark paths. Those remain unguarded here.
  // The restoring transaction runs noteEdit -> scheduleAutosave, so the flag is set and the
  // deadline re-armed — while the editor's serialized HTML is byte-identical to what the server
  // confirmed. Had the timer been allowed to fire, `save()` would have hit
  // `if (isAlreadySaved(...)) { onSaved(); return }` (useDocumentSave.ts:186) and written NOTHING.
  // Walking away one tick earlier must not be reported as losing the write that provably wasn't one.
  // RED: expected "error" to not be called at all, but actually been called 1 times — the record is
  // ["Pending document save abandoned before it completed"]. hasPendingEditRef is still true because
  // the timer never fired, so the []-scoped cleanup logs over content the server provably holds.
  // RED 2026-07-30, awaiting the H9.4 green that moves the clear site.
  it.skip('records nothing when the editor unmounts after an edit was reverted to the saved content', async () => {
    const { unmount } = await renderCreatedDocument()

    armServerConfirmsSavedContent()

    // Baseline: one real autosave lands, so lastSavedContentRef holds exactly what the editor holds
    // and the flag is back to false (the timer fired). What the server was handed is pinned as an
    // argument rather than inferred from a green badge — this is what makes "nothing was abandoned" a
    // fact about the SERVER's copy and not merely about a flag: the bytes it asserts are the same
    // bytes the editor is asserted to hold at unmount.
    await typeIntoEditor(SAVED_PLAIN)
    await crossDebounceBoundary()
    expectBaselineSaveOnWire()
    expectSavedBadge()
    expect(dispatchBeforeUnload()).toBe(false)

    // Type one more word and take it straight back out, clock frozen inside the debounce window.
    await typeIntoEditor(EDITED_PLAIN)
    await typeIntoEditor(SAVED_PLAIN)
    // Exclusively dirty — the badge must have moved OFF «Сохранено», not merely acquired --dirty
    // alongside it, which is how a green that renders both branches would slip past a bare toHaveClass.
    expectOnlyDirtyBadge()
    // The non-vacuity gate for the `false` above: ManualEditor registers the beforeunload listener
    // only while hasUnsavedChanges is true, so a regression that never arms it satisfies every
    // toBe(false) in this file. Observing true exactly here is what makes the earlier false mean
    // "stood down" instead of "was never there".
    expect(dispatchBeforeUnload()).toBe(true)
    // "A deadline is armed" is deliberately NOT asserted via vi.getTimerCount(): the observed count
    // here is 3, not 1 — every input event arms ProseMirror-internal ticks beside our debounce, so the
    // global count is a third-party number that would fail for reasons pointing nowhere near this
    // record. The armed deadline is proven by the record itself: hasPendingEditRef is written in
    // exactly one place (useAutosave's arm), so a fired assertion below IS the timer's fingerprint.
    // ...and the armed write has nothing to carry: the editor holds the exact bytes asserted on the
    // wire above. This, not the dirty flag, is why the record must stay silent.
    expect(editorContentHtml()).toBe(SAVED_CONTENT)
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    unmount()

    expectNoAbandonmentRecorded()
  })

  // (b) Manual Сохранить inside the gap. `ManualEditor` wires the button straight to `save`
  // (onSave={save}), bypassing the scheduler entirely: the write goes out, resolves, the badge reads
  // «Сохранено» — and the timer the keystroke armed is still sitting there with the flag true. Unmount
  // before the deadline and the app reports an abandoned write while its own beforeunload guard,
  // reading hasUnsavedChanges at the same instant, reports nothing pending. Two answers, one moment.
  //
  // ManualEditor.manualSaveTrailingAutosave.test.tsx already crosses this window and asserts the
  // trailing PUT is suppressed. It never spies console.error, so the record is nobody's assertion.
  //
  // RED: expected "error" to not be called at all, but actually been called 1 times — same record,
  // same cause. The button bypasses the scheduler, so nothing clears the flag the keystroke set.
  // RED 2026-07-30, awaiting the H9.4 green that moves the clear site.
  it.skip('records nothing when a manual save inside the debounce gap already persisted the edit', async () => {
    const { unmount } = await renderCreatedDocument()

    armServerConfirmsSavedContent()

    // One edit, deadline armed, nothing sent — genuinely unsent work, and the one moment in this
    // case where the guard SHOULD be armed. Asserting it here is what stops the closing false below
    // from passing vacuously on a listener that was never registered.
    await typeIntoEditor(SAVED_PLAIN)
    expect(documentApi.saveDocument).not.toHaveBeenCalled()
    expect(dispatchBeforeUnload()).toBe(true)

    // Part-way through the window the user clicks Сохранить rather than waiting.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CLICK_AT_MS)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить' }))
    await flushMicrotasks()

    expectBaselineSaveOnWire()
    // The bytes the click put on the wire are the bytes the editor still holds — asserted here rather
    // than inferred from the green badge, so "nothing was abandoned" is a fact about the server's copy
    // in this case exactly as it is in case (a).
    expect(editorContentHtml()).toBe(SAVED_CONTENT)
    // The work IS on the server, and the app says so twice over — badge and browser guard agree.
    expectOnlySavedBadge()
    expect(dispatchBeforeUnload()).toBe(false)
    // Still short of the deadline the keystroke armed — the stale timer is what carries the flag. Not
    // asserted via the global timer count, for the reason spelled out in case (a).

    unmount()

    // The third voice must agree with the other two. It does not today.
    expectNoAbandonmentRecorded()
  })
})

// The positive counterpart — unmount inside the debounce gap over an edit the server never received
// MUST still record — is not restated here: ManualEditor.autosaveAbandonRecord.test.tsx already owns
// it ('records the abandonment when the editor unmounts inside the debounce gap'), and a second copy
// is how the pair that must stay opposite drifts.
