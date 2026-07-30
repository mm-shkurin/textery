import { expect, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import * as documentApi from '../../api/documentApi'
import { defer, flushMicrotasks } from './ManualEditor.autosave.testSupport'
import { SAVE_BUTTON_LABEL } from './ManualEditor.saveStatus.testSupport'

// The H9.4 ABANDONMENT vocabulary: what the app must and must not leave behind when the editor dies
// with a write unfinished, plus the servers and the wire assertions the abandonment suites drive it
// with. Split out of ManualEditor.autosaveFixture, which had 17 lines of headroom against the 200-line
// limit and was already carrying three unrelated concerns (fixture constants, the failure server, the
// backoff window). The three suites that observe the diagnostic sink — autosaveAbandonRecord,
// autosaveAbandonFalseRecord, autosaveBackoffWindowVisibility — are exactly this module's consumers,
// so the split falls on a real seam rather than at a line count.

// The two directions the scenario's own RED cannot see. It unmounts at ONE instant — inside a
// backoff gap, with a timer object pending — and asserts the abandonment record appears. That
// leaves both neighbours open:
//
//   - UNCONDITIONALLY logging in the []-scoped cleanup passes it exactly, and then every ordinary
//     back-out of a fully-saved document writes a false abandonment into the app's only diagnostic
//     sink. The existing unmount test (ManualEditor.autosave.test.tsx) does not spy console.error.
//   - keying the record on "a retry timer exists" passes it too, and misses the FOUR in-flight
//     request sub-windows the same ~7-second ladder contains, where retryTimerRef is null and the
//     write is just as abandoned. The record has to key on "there is an unfinished write".
//
// CONSTRAINT ON THE GREEN, and it is not optional — this file and its negative twin
// (ManualEditor.autosaveAbandonFalseRecord.test.tsx) pull in opposite directions on the SAME flag,
// so a green that satisfies one by the obvious route breaks the other:
//
//   The twin's manual-save case wants hasPendingEditRef cleared wherever save() RUNS. Do that
//   literally and the init-failure case below goes red, because !documentId is one of the paths
//   save() runs on — and that case is the only test in the repo standing between a user and total,
//   silent loss of everything typed into a document that was never created.
//
//   Clear the flag where a write was decided against ON THE MERITS (isAlreadySaved: the server
//   already has these bytes). Do NOT clear it where writing was IMPOSSIBLE (!documentId: the bytes
//   exist and have nowhere to go). Those two early returns look alike and mean opposite things.

// What the app must leave behind when a pending write is abandoned by unmount. console.error is the
// app's only diagnostic sink (there is no reporting backend), so this is the minimum viable record —
// deliberately the same sink useDocumentSave already writes the rejection itself to.
//
// An independently-written copy of autosaveAbandonment.ts:17 rather than an import, and that is the
// tripwire by design: importing production's constant would make every assertion below tautological.
export const ABANDONED_SAVE_LOG = 'Pending document save abandoned before it completed'

// The abandonment record, asserted whole: it happened, it happened ONCE, and it is exactly this one
// message. `toHaveBeenCalledWith` pins the FULL argument list rather than argument 0 alone — a stray
// second argument is a different record — and the count is what separates "recorded" from "recorded
// once per failed attempt already logged". Shared by every suite that observes the sink so the sites
// cannot drift into asserting different notions of "recorded".
export function expectAbandonmentRecorded() {
  expect(console.error).toHaveBeenCalledTimes(1)
  expect(console.error).toHaveBeenCalledWith(ABANDONED_SAVE_LOG)
}

// The negative twin, spelled once. The cases that assert it are the guards against a green that logs
// unconditionally, and they must all mean the same thing: the sink was not touched at all.
export function expectNoAbandonmentRecorded() {
  expect(console.error).not.toHaveBeenCalled()
}

// Drops the diagnostics a FAILED ATTEMPT already wrote (useDocumentSave logs every rejection) so the
// count in expectAbandonmentRecorded speaks only for the unmount. Named for that intent rather than
// left as a bare `vi.mocked(console.error).mockClear()` in a case body: the spy belongs to
// useAutosaveFailureFakeTimers, and a raw reach into it says nothing about why.
export function discardAttemptDiagnostics() {
  vi.mocked(console.error).mockClear()
}

// A server that accepts the request and never answers — the write is in flight for the rest of the
// test. This is the sub-window where retryTimerRef is null and the write is nonetheless abandoned the
// instant the component dies, so it must be arm-able by name beside the settling servers.
export function armServerNeverSettles() {
  vi.mocked(documentApi.saveDocument).mockReturnValue(defer().promise)
}

// Nothing reached the wire at all. The count AND the absence of any arguments: `not.toHaveBeenCalled`
// is the whole claim, and naming it keeps the abandonment suites from each reaching into the mocked
// module directly for the one fact they most often need.
export function expectNoSaveOnWire() {
  expect(documentApi.saveDocument).not.toHaveBeenCalled()
}

// The strictly stronger form of "no request yet": there is no request POSSIBLE. Clicks the manual
// Сохранить — the one path to `save()` that does not go through the debounce — and shows the wire is
// still empty afterwards.
//
// The aria-disabled assertion is what makes the silence attributable. ManualEditorToolbar renders the
// button with `aria-disabled={isSaving}` and never the native `disabled` attribute, so the click
// genuinely dispatches; observing `false` here rules out "the button was inert" and leaves only
// `useDocumentSave.ts:172`'s `if (!documentId) return` — the null id — as the reason nothing was sent.
export async function expectManualSaveCannotReachTheWire() {
  const saveButton = screen.getByRole('button', { name: SAVE_BUTTON_LABEL })
  expect(saveButton).toHaveAttribute('aria-disabled', 'false')
  fireEvent.click(saveButton)
  await flushMicrotasks()
  expectNoSaveOnWire()
}
