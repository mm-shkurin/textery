import { afterEach, beforeEach, expect, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import type { SaveDocumentResult } from '../../api/documentApi'
import { AUTOSAVE_DEBOUNCE_MS } from '../../hooks/useAutosave'
import {
  expectInitFailedBanner,
  expectOnlyDirtyBadge,
  expectOnlyInitFailedBadge,
} from './ManualEditor.saveStatus.testSupport'

// Debounced-autosave debounce interval (ms). Re-exported from the hook rather than redeclared:
// the tests must advance the boundary PRODUCTION uses, so retuning the debounce fails the timer
// tests loudly instead of letting them advance a stale 1000 and silently keep passing.
export { AUTOSAVE_DEBOUNCE_MS } from '../../hooks/useAutosave'

// The document the shared fixture creates. Assertions reference these instead of re-hardcoding
// 'doc-1'/7, so the fixture and every expectation that quotes it move together.
export const CREATED_DOCUMENT_ID = 'doc-1'
export const CREATED_VERSION = 7

// A generous timer advance for the H9.3 failure-taxonomy tests: big enough that the whole
// capped-backoff retry schedule plays out inside it, so assertions never hardcode green's exact
// per-attempt delays. Shared by the retry/expired-session/queued-edit suites (single source).
export const RETRY_WINDOW_MS = 60_000

// Fake-timer settle: drain the pending microtask queue (resolved/rejected save promises,
// their .then/.catch, and the React state updates they schedule) without advancing wall
// clock. Must run under vi.useFakeTimers(); wraps in act() so the flushed updates commit.
export async function flushMicrotasks() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0)
  })
}

// Installs the fake-timer lifecycle shared by every autosave suite: fake timers on for each test,
// all mocks restored/cleared and real timers back after. Call once inside a describe block — it
// registers the beforeEach/afterEach hooks at that scope. Console output is left ALONE: suites that
// exercise a failure path opt into silencing separately (see silenceConsoleError), so a suite whose
// diagnostics matter keeps them.
export function useAutosaveFakeTimers() {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    vi.useRealTimers()
  })
}

// Opt-in companion for the failure suites: the save .catch's console.error is this app's only
// diagnostic and would otherwise print a real-looking failure into a passing run. Kept separate from
// useAutosaveFakeTimers so silencing is a choice each suite makes, not a side effect of wanting fake
// timers — the restore is handled by useAutosaveFakeTimers' restoreAllMocks.
function silenceConsoleError() {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })
}

// The fake-timer + silenced-console lifecycle used by the autosave FAILURE suites.
export function useAutosaveFailureFakeTimers() {
  useAutosaveFakeTimers()
  silenceConsoleError()
}

// A promise whose settlement the test controls, so a save can be held "in flight" while further
// edits land. Exposes BOTH resolve and reject: the coalesce/out-of-order suites drive the resolve
// path, the failure suites drive the reject path. The no-op .catch keeps a rejection from
// surfacing as an unhandled rejection before the hook attaches its own handler.
export interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (reason: unknown) => void
}

export function defer<T = SaveDocumentResult>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  promise.catch(() => {})
  return { promise, resolve, reject }
}

// The document type every autosave fixture mounts with, and therefore the type its init is asserted to
// have requested. Named because nothing else enforces that the type a fixture mounts is the one it pins.
export const EDITOR_DOCUMENT_TYPE = 'doklad'
const EDITOR_DOCUMENT_TYPE_LABEL = 'Доклад'

// The mount contract shared by both starting points below: same props, same settle. Spelled once so a
// prop change cannot land on one fixture and be missed on the other.
async function mountEditor() {
  const rendered = render(
    <ManualEditor
      documentType={EDITOR_DOCUMENT_TYPE}
      documentTypeLabel={EDITOR_DOCUMENT_TYPE_LABEL}
      onBack={vi.fn()}
    />,
  )
  await flushMicrotasks()
  return rendered
}

// That init ran exactly once and asked for the fixture's document type. Shared by both entry proofs: a
// `createDocument` mock that was never invoked satisfies every downstream assertion about what init
// produced — in the success fixture and the failure fixture alike.
//
// The idempotency key is minted by `crypto.randomUUID()` (useDocumentInit.ts:53), so its VALUE is the
// one thing here a test cannot know. Its SHAPE is not: pinned to the v4 form rather than left as
// `expect.any(String)`, which an empty string also satisfies — and an empty key is precisely what the
// ref's `if (!idempotencyKeyRef.current)` guard exists to stop reaching the server.
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/
function expectInitRequested() {
  expect(documentApi.createDocument).toHaveBeenCalledTimes(1)
  expect(documentApi.createDocument).toHaveBeenCalledWith(
    EDITOR_DOCUMENT_TYPE,
    expect.stringMatching(UUID_V4),
  )
}

// Renders a ManualEditor whose initial createDocument has already resolved to a fresh draft at version
// 7 — the common starting point for the autosave scenarios. Returns the render result so a suite that
// needs to unmount (pending-timer cancellation) reuses this same fixture.
//
// The entry proof is the mirror of renderFailedInitDocument's: `expectOnlyDirtyBadge` is reachable only
// once `documentId` is non-null (ManualEditorSaveStatus.tsx:25,45), so it is the screen-level statement
// that the id ARRIVED — the premise every case built on this fixture assumed and none asserted.
export async function renderCreatedDocument() {
  vi.mocked(documentApi.createDocument).mockResolvedValue({
    documentId: CREATED_DOCUMENT_ID,
    status: 'draft',
    version: CREATED_VERSION,
  })
  const rendered = await mountEditor()
  expectInitRequested()
  expectOnlyDirtyBadge()
  return rendered
}

// The opposite starting point to renderCreatedDocument: an editor whose createDocument REJECTED, so
// `documentId` stays null for the rest of the test while the editor is mounted and fully typeable — the
// state ManualEditor.tsx describes as «with no documentId there is nothing to save TO».
//
// Rejecting with a textless Error keeps this helper out of the business of WHICH failure text reaches
// the screen (ManualEditor.initError.test.tsx owns that) while still driving the same catch:
// `describeFailure` falls back to CREATE_FAILED_MESSAGE, which is what the banner below is pinned to.
//
// The three assertions are the entry proof, not decoration: without them a case built here could be
// running against an init that silently succeeded, and every "nothing was saved" assertion downstream
// would hold for the wrong reason. All three are screen-level, and each says what the others cannot —
// init was ASKED (so the null id is the rejection's doing, not a mock nobody called), the badge is the
// `--failed` branch (reachable only while `documentId` is null AND creation is over), and the banner
// carries exactly the create-failure text with no save banner beside it.
export async function renderFailedInitDocument() {
  vi.mocked(documentApi.createDocument).mockRejectedValue(new Error(''))
  const rendered = await mountEditor()
  expectInitRequested()
  expectOnlyInitFailedBadge()
  expectInitFailedBanner()
  return rendered
}

// Replaces the editor's text and fires the input event — one user edit, WITHOUT crossing the
// debounce boundary. Split out from typeAndFireAutosave because the coalescing suites need an
// edit to land mid-flight while the clock stays put.
export async function typeIntoEditor(text: string) {
  const contentArea = screen.getByTestId('editor-content-area')
  contentArea.textContent = text
  await act(async () => {
    fireEvent.input(contentArea)
  })
}

// The editor's rendered HTML, read through the same test id typeIntoEditor writes through. Named so
// a suite asserting what the editor holds after a save resolved does not respell the selector the
// helper above already owns.
export function editorContentHtml(): string {
  return screen.getByTestId('editor-content-area').innerHTML
}

// Advances past the debounce boundary so a pending debounced autosave fires, then settles its promise.
export async function crossDebounceBoundary() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS)
  })
  await flushMicrotasks()
}

// Types text into the editor, fires the input event, and crosses the debounce boundary so the
// single debounced autosave fires and its promise settles.
export async function typeAndFireAutosave(text: string) {
  await typeIntoEditor(text)
  await crossDebounceBoundary()
}
