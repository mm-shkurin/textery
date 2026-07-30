import { expect, vi } from 'vitest'
import { act, screen } from '@testing-library/react'
import type { HttpError } from '../../../../shared/api/httpClient'
import * as documentApi from '../../api/documentApi'
import type { SaveDocumentResult } from '../../api/documentApi'
import {
  CREATED_DOCUMENT_ID,
  CREATED_VERSION,
  RETRY_WINDOW_MS,
  flushMicrotasks,
  renderCreatedDocument,
  typeAndFireAutosave,
} from './ManualEditor.autosave.testSupport'
import { SAVE_ERROR_TESTID, expectSavedBadge } from './ManualEditor.saveStatus.testSupport'

// The autosave FIXTURE vocabulary: the text a failure suite types, the HTML it expects on the wire,
// and the OCC versions those writes carry. A plain .ts module rather than more exports on
// ManualEditor.autosave.testSupport.tsx — that file exports a component-rendering helper, so every
// non-component export added to it trips react(only-export-components). Nothing here needs JSX.

// The paragraph wrapper Tiptap's schema puts around one line of typed text. Naming the relationship
// is what keeps `typeIntoEditor(SAVED_PLAIN)` and the `saveDocument(_, SAVED_CONTENT, _)` argument
// assertion from drifting apart: nothing else enforces that the text a test types and the HTML it
// expects on the wire are the same edit.
export const asParagraph = (text: string) => `<p>${text}</p>`

// The three-step fixture the dirty-guard failure suites share: a baseline line the server confirms,
// the edit made on top of it whose save fails, and a later revision used to prove the write path is
// still alive after the guard settled. Shared rather than respelled per file because those suites
// are deliberately written as INVERSE assertions over one fixture — a per-file copy is exactly how
// two tests that must stay opposite drift into quietly testing the same thing.
export const SAVED_PLAIN = 'hello world'
export const EDITED_PLAIN = 'hello world edited'
export const REVISED_PLAIN = 'hello world again'
export const SAVED_CONTENT = asParagraph(SAVED_PLAIN)
export const EDITED_CONTENT = asParagraph(EDITED_PLAIN)
export const REVISED_CONTENT = asParagraph(REVISED_PLAIN)

// The versions the baseline save and a later successful save confirm. Derived from CREATED_VERSION
// rather than written as bare 8 and 9: the OCC tuples the suites assert are only meaningful as
// "one past what the fixture started at", and retuning CREATED_VERSION must not leave them
// asserting a fiction that still passes.
export const SAVED_VERSION = CREATED_VERSION + 1
export const RETRY_VERSION = SAVED_VERSION + 1

// The abandonment record's vocabulary — ABANDONED_SAVE_LOG, expectAbandonmentRecorded and its
// negative twin — moved to ManualEditor.autosaveAbandonFixture.ts, together with the never-settling
// server and the wire assertions the abandonment suites drive. This file was at 183 of 200 lines and
// the record is a separable concern with its own three consumers.

// A server that confirms every write, echoing back the fixture's baseline content at the version one
// past what the document was created at. Shared rather than respelled per case: the literal was
// spelled twice inside a single suite and again across the sibling autosave files, and a per-site copy
// is how one of them ends up arming a version the OCC assertions no longer describe.
export function armServerConfirmsSavedContent() {
  vi.mocked(documentApi.saveDocument).mockResolvedValue({
    status: 'saved',
    version: SAVED_VERSION,
    content: SAVED_CONTENT,
  })
}

// The baseline write, asserted on the wire: that exactly `nth` saves have gone out, and that the
// `nth` one carried the document, the baseline bytes, and the version the document was created at.
// Extracted because this OCC triple was spelled verbatim at four sites (twice in the abandonment
// suites, twice inside this module) — and the triple only means anything if all four agree.
export function expectBaselineSaveOnWire(nth = 1) {
  expect(documentApi.saveDocument).toHaveBeenCalledTimes(nth)
  expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
    nth,
    CREATED_DOCUMENT_ID,
    SAVED_CONTENT,
    CREATED_VERSION,
  )
}

// Deliberately no `expectDebounceStillArmed()` helper here. It existed briefly, asserting
// `vi.getTimerCount()).toBe(1)` on the argument that useAutosave calls clearPending() before every
// setTimeout so at most one debounce timer can exist. That argument is sound about OUR timers and
// wrong about the number: run un-skipped, a case with two input events reports 3 — every input event
// arms ProseMirror-internal ticks too, the same third-party coupling the sibling debounce case already
// rejected `toBe(1)` for. A global count cannot express "one autosave is pending"; the app has no
// scoped signal for it, so cases assert the consequence (no request on the wire, and the record) and
// leave the timer unasserted.

// Runs the whole capped-backoff retry schedule to completion and settles whatever it fired, plus
// any stale debounce armed during the wait. Extracted because the act/advanceTimersByTimeAsync/
// flushMicrotasks composition is infrastructure the failure suites repeated verbatim — and because
// RETRY_WINDOW_MS is a detail of HOW the schedule is drained, not something a test narrative should
// have to name.
export async function playOutRetrySchedule() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(RETRY_WINDOW_MS)
  })
  await flushMicrotasks()
}

// A server that transiently refuses every write. Typed as HttpError, not left as a bare object
// literal: isTransientFailure narrows through isHttpError, so a fixture that quietly stopped
// satisfying that shape would schedule NO retry at all — and a suite asserting what happens inside
// the backoff window would then be observing a window that never opened.
const TRANSIENT_SERVER_REJECTION: HttpError = { status: 503, body: {} }

// The 5xx this origin can ACTUALLY emit — exception_handlers.py returns 500 only, gated by
// `npm run check:ingress`. 503 above is the sole carve-out in mayHaveLandedServerSide and therefore
// the one branch that KEEPS the dirty guard's memory; a suite driven through 500 exercises the
// branch production really takes, the one that NULLS it. Shared rather than respelled per suite so
// the H9.4 guard suites are provably talking about the same server.
export const PRODUCTION_SERVER_ERROR: HttpError = { status: 500, body: {} }

// That server, armed. A named arm beside the constant so a case narrating "the server refuses" does
// not have to spell `vi.mocked(...).mockRejectedValue(...)` in its body — the same reason
// armServerConfirmsSavedContent exists for the accepting server.
export function armServerRefusesWithProductionError() {
  vi.mocked(documentApi.saveDocument).mockRejectedValue(PRODUCTION_SERVER_ERROR)
}

// Puts the editor INSIDE the H9.3 capped-backoff window and proves it got there. Renders a fresh
// document, arms a server that transiently refuses every write, and lands one user edit — so by the
// time this returns, attempt 1 has fired and been rejected while the ladder still has attempts left.
//
// The two assertions are the entry proof, not decoration: the count pins that we are past attempt 1
// and not yet past the rest, and the OCC triple pins that the attempt which rejected really was the
// user's edit at the document's current version rather than some other write the case never asked
// for. Without them a case built on top of this could be describing the wrong instant, or a window
// opened by something else entirely.
//
// Returns the render result so a case needing `container` or `unmount` reuses this same fixture.
export async function enterBackoffWindow() {
  const rendered = await renderCreatedDocument()

  vi.mocked(documentApi.saveDocument).mockRejectedValue(TRANSIENT_SERVER_REJECTION)

  await typeAndFireAutosave(SAVED_PLAIN)
  expectBaselineSaveOnWire()

  return rendered
}

// The tail stub the revert suites leave armed behind their scripted first two outcomes. It ECHOES
// back the content it was handed rather than returning a fixed body: a fixed body would differ from
// what a later save sent, and the resolve handler would adopt it into the editor, rewriting the
// user's text underneath the assertions as a pure artefact of the stub.
export async function echoSavedAtRetryVersion(
  _documentId: string,
  content: string,
): Promise<SaveDocumentResult> {
  return { status: 'saved', version: RETRY_VERSION, content }
}

// The prologue both revert suites open with: a baseline save the server confirms (so the dirty guard
// has a remembered content at all), then an edit on top of it whose save fails TRANSIENTLY — no
// banner, a backoff pending, the cycle still "in flight". Shared rather than respelled per file for
// the same reason the fixture constants are: the two suites are deliberate inverse assertions over
// one setup, and a per-file copy of the setup is how they drift into testing different things.
// Parameter-free on purpose — WHICH failure the second save returns is scripted by each suite's own
// mock before calling this, and that choice is the whole point of the pair.
export async function saveBaselineThenTransientFailure() {
  await typeAndFireAutosave(SAVED_PLAIN)
  expectBaselineSaveOnWire()
  expectSavedBadge()

  await typeAndFireAutosave(EDITED_PLAIN)
  expect(documentApi.saveDocument).toHaveBeenCalledTimes(2)
  expect(documentApi.saveDocument).toHaveBeenNthCalledWith(
    2,
    CREATED_DOCUMENT_ID,
    EDITED_CONTENT,
    SAVED_VERSION,
  )
  expect(screen.queryByTestId(SAVE_ERROR_TESTID)).toBeNull()
}
