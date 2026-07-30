import { expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { ManualEditor } from '../ManualEditor'
import * as documentApi from '../../api/documentApi'
import { flushMicrotasks } from './ManualEditor.autosave.testSupport'
import {
  expectInitFailedBanner,
  expectOnlyDirtyBadge,
  expectOnlyInitFailedBadge,
} from './ManualEditor.saveStatus.testSupport'

// The two mounted starting points every autosave suite begins from, split out of
// ManualEditor.autosave.testSupport so the timer/typing infrastructure can stay a plain .ts module:
// only the helpers below need JSX, and keeping them here is what lets the other file drop its .tsx.

// The document the shared fixture creates. Assertions reference these instead of re-hardcoding
// 'doc-1'/7, so the fixture and every expectation that quotes it move together.
export const CREATED_DOCUMENT_ID = 'doc-1'
export const CREATED_VERSION = 7

// The document type every autosave fixture mounts with, and therefore the type its init is asserted to
// have requested. Named because nothing else enforces that the type a fixture mounts is the one it pins.
const EDITOR_DOCUMENT_TYPE = 'doklad'
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
