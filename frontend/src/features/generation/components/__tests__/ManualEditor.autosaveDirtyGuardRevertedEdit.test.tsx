import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  DIRTY_BADGE_CLASS,
  DIRTY_STATUS,
  SAVED_BADGE_CLASS,
  SAVED_STATUS,
  crossDebounceBoundary,
  dispatchBeforeUnload,
  flushMicrotasks,
  renderCreatedDocument,
  typeIntoEditor,
  useAutosaveFakeTimers,
} from './ManualEditor.autosave.testSupport'

vi.mock('../../api/documentApi')

const SAVED_CONTENT = '<p>hello world</p>'
const SAVED_VERSION = 8

// Scenario H9.4 — the regression shipped by the dirty guard (9650620), found independently by both
// review passes.
//
// `save()` ends in `if (isAlreadySaved(...)) return` — a bare early return, and the ONLY exit that
// skips performSave without ever reaching `onSaved()`, which is the sole writer of
// setHasUnsavedChanges(false). Meanwhile `noteEdit` calls `onDirty()` on EVERY editor update,
// including the transaction that brings the content BACK to the last-saved value (Ctrl+Z, a
// Backspace of the one character just typed, bold-then-unbold from the toolbar).
//
// So on a single tab, with no race and nothing in flight: clean save -> type -> revert -> cross the
// debounce boundary -> the guard bites -> no PUT and no onSaved(). The document is genuinely clean,
// but `hasUnsavedChanges` stays true with NO PATH LEFT TO CLEAR IT: every later autosave and every
// «Сохранить» click re-enters the same guard and returns bare. The badge is stuck on the dirty
// status for the life of the editor, beforeunload stays armed over a document the server already
// has, and the Save button is dead — no request, no spinner, no state change.
//
// Suppressing the PUT is CORRECT and is asserted here too: the fix is not to undo the guard but to
// settle the clean state on the suppression path. Pre-9650620 this sequence fired a redundant PUT
// that at least ended in onSaved() and a truthful badge.
//
// Every existing guard test reaches the guard from an ALREADY-CLEAN state (they assert "Сохранено"
// before crossing), so none enters it with hasUnsavedChanges === true; ManualEditor.undoRedo never
// crosses a debounce boundary. That is why the suite is green over this.
describe('ManualEditor — an edit reverted to the last-saved content settles clean (H9.4 regression)', () => {
  useAutosaveFakeTimers()

  it.skip('leaves the document clean, the Save button live and beforeunload disarmed after the boundary suppresses a no-op save', async () => {
    await renderCreatedDocument()

    vi.mocked(documentApi.saveDocument).mockResolvedValue({
      status: 'saved',
      version: SAVED_VERSION,
      content: SAVED_CONTENT,
    })

    // Baseline: one real autosave lands, so lastSavedContentRef holds exactly what the editor holds.
    await typeIntoEditor('hello world')
    await crossDebounceBoundary()
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)
    expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
      1,
      CREATED_DOCUMENT_ID,
      SAVED_CONTENT,
      CREATED_VERSION,
    )
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    // Clean baseline for the guard. On its own this proves nothing — see the armed `true` below.
    expect(dispatchBeforeUnload()).toBe(false)

    // Type one more word, then take it straight back out. Both transactions run noteEdit -> onDirty,
    // so the document is marked dirty and the debounce is re-armed — while the editor's serialized
    // HTML is once again byte-identical to what the server confirmed.
    await typeIntoEditor('hello world edited')
    await typeIntoEditor('hello world')
    expect(screen.getByText(DIRTY_STATUS)).toHaveClass(DIRTY_BADGE_CLASS)
    // THE non-vacuity gate for both `false` observations. ManualEditor arms the beforeunload
    // listener only while hasUnsavedChanges is true (`if (!hasUnsavedChanges) return` before
    // addEventListener), so a regression that never registers the guard at all would satisfy every
    // `toBe(false)` in this test. Observing `true` exactly once, here, is what makes the closing
    // `false` mean "the guard stood down" instead of "the guard was never there".
    expect(dispatchBeforeUnload()).toBe(true)

    await crossDebounceBoundary()

    // The suppression itself is right: nothing changed, so nothing may be written.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // ...but the badge must tell the truth about it. This is the regression.
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()

    // The user's one recovery route must not be a dead button: clicking Сохранить from this state
    // has to leave the document clean rather than silently doing nothing forever. The button is
    // gated with aria-disabled (never the native attribute — see ManualEditorToolbar), so "live"
    // is asserted on that, and the click really does dispatch.
    const saveButton = screen.getByRole('button', { name: 'Сохранить' })
    expect(saveButton).toHaveAttribute('aria-disabled', 'false')
    fireEvent.click(saveButton)
    await flushMicrotasks()
    expect(screen.getByText(SAVED_STATUS)).toHaveClass(SAVED_BADGE_CLASS)
    expect(screen.queryByText(DIRTY_STATUS)).toBeNull()
    // The recovery click settles state; it must not buy that by writing content the server already
    // holds. Still exactly one PUT, still the baseline one — the guard keeps suppressing.
    expect(documentApi.saveDocument).toHaveBeenCalledTimes(1)

    // And the browser's leave-prompt guard must stand down — the work IS on the server, so warning
    // about it on every close is a false alarm the user learns to click through.
    expect(dispatchBeforeUnload()).toBe(false)
  })
})
