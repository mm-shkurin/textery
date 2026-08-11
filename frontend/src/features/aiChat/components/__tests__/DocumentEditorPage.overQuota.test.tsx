import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { DocumentEditorPage } from '../DocumentEditorPage'
import { loadEditorDocument } from '../../api/editorDocumentApi'
import { loadEditQuota, type EditQuotaState } from '../../api/editQuotaApi'

// Story 19, Frontend Scenario 0.2 — "An account over its daily quota cannot type an instruction"
// (`tests/02_UI_Tests.md`).
//
// WHY THIS EXISTS ALONGSIDE THE SELENIUM TEST. The acceptance test spends a real day's quota and
// can therefore only ever observe the exhausted branch. It cannot tell a conditional composer
// from one that is disabled for everybody — a chat panel that never enables its input passes it.
// The third case below is that missing half, and it is what this unit is for.
//
// SEAM. `loadEditQuota` (account-scoped, `../../api/editQuotaApi`) is the contract addition
// scenario 0.2 forces open: `resets_at` today lives only in the 429 body of `POST /ai-edits`,
// which arrives after the user has already typed. Its wire mapping is `red-frontend-api`'s
// scope; here it is a mocked module identity and a type the page must agree with.
//
// DELIBERATELY NOT PINNED: the quota read's own loading and failure states (scenario 8.8), and
// the CONTENT of the revisions panel. "Remains usable" is asserted here as the quota branch
// leaving the revisions control alive and its panel openable — the rows inside it are read by
// `GET /revisions`, which scenario 1.3 owns and which this test must not pull forward.

const MESSAGE_INPUT = 'ai-chat-message-input'
const SEND_BUTTON = 'ai-chat-send-button'
const QUOTA_RESET_HINT = 'ai-chat-quota-reset-hint'
const QUOTA_RESET_HINT_LEAD = 'ai-chat-quota-reset-hint-lead'
const REVISIONS_TOGGLE = 'ai-chat-revisions-toggle'
const REVISIONS_PANEL = 'ai-chat-revisions-panel'
const AI_CHAT_PANEL = 'ai-chat-panel'

// Every testid above is copied from `acceptance/statements/frontend/ai_chat/over_quota_statements.py`.
// If the two lists ever disagree the layers specify two different UIs and one of them passes
// against a screen no user sees.
const EXPECTED_RESET_HINT_LEAD = 'Дневной лимит правок исчерпан'

// A NON-CANONICAL instant on purpose: a Moscow offset, not `Z`, and no fractional seconds. This is
// the case that pins review follow-up (an) — `data-resets-at` must carry the wire string the API
// returned, byte for byte. Any `new Date(...).toISOString()` on the way to the attribute rewrites
// this to `2026-08-10T21:00:00.000Z` and fails here, which is precisely the fragility the Selenium
// layer's byte-equality assertion would otherwise discover across two serializations.
const RESETS_AT_WIRE = '2026-08-11T00:00:00+03:00'

const DOCUMENTS_LIST_PATH = '/documents'
const DOCUMENT_ID = '7a3d5e19-2c64-4b08-8f52-91ad3e7c0b6f'
const DOCUMENT = { documentId: DOCUMENT_ID, content: '<p>Введение к докладу</p>', version: 3 }

// Typed as `EditQuotaState`, not as an inline structural literal. The inline shape re-declared the
// contract instead of depending on it: renaming `resetsAt` in `editQuotaApi.ts` — or widening it to
// `string` and dropping the `null` arm — would leave this file type-checking and green against a
// module it no longer agrees with, which is the whole reason the seam is a real module and not a
// bare `vi.fn()`.
const OVER_QUOTA: EditQuotaState = { exhausted: true, resetsAt: RESETS_AT_WIRE }
const WITHIN_QUOTA: EditQuotaState = { exhausted: false, resetsAt: null }

vi.mock('../../api/editorDocumentApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/editorDocumentApi')>()
  return { ...actual, loadEditorDocument: vi.fn() }
})
vi.mock('../../api/editQuotaApi', () => ({ loadEditQuota: vi.fn() }))

const loadEditorDocumentMock = vi.mocked(loadEditorDocument)
const loadEditQuotaMock = vi.mocked(loadEditQuota)

// Rendered under `StrictMode` — the same wrapper `main.tsx` puts around `App` — because that is
// what makes the call-count assertions below mean anything. Scenario 0.1 shipped
// `toHaveBeenCalledExactlyOnceWith` outside StrictMode and recorded the hole (follow-up (k)): a
// naive `useEffect` fetch passes once-per-render assertions in the test and double-fires in dev.
// Green closed it for the document load with a ref placed BEFORE the fetch — the existing
// `useDocumentInit` cancel-flag pattern does not work, it suppresses the second setState but not
// the second request. The quota read is a NEW fetch that inherits none of that, so it is pinned
// here from the start rather than discovered later.
function renderEditorFor(quota: EditQuotaState) {
  loadEditorDocumentMock.mockResolvedValue(DOCUMENT)
  loadEditQuotaMock.mockResolvedValue(quota)
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={[`${DOCUMENTS_LIST_PATH}/${DOCUMENT_ID}`]}>
        <Routes>
          <Route path="/documents/:documentId" element={<DocumentEditorPage />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
  )
}

// Both loads, pinned together, in every case. Two separate jobs:
//
// COUNT — an unpinned count passes a page that re-reads on every render (a request per keystroke
// once scenario 1.1 lands a composer in this panel). This is 0.1's lesson verbatim.
//
// ARGUMENTS — `loadEditQuota` is asserted to be called with NO arguments, which is the only thing
// that holds green to `editQuotaApi.ts`'s stated design: the daily limit belongs to the ACCOUNT,
// and threading a `documentId` through would invite a per-document reading of a limit that is not
// per-document. Nothing else in either layer would fail if green passed one.
function expectBothLoadsIssuedExactlyOnce() {
  expect(loadEditorDocumentMock).toHaveBeenCalledExactlyOnceWith(DOCUMENT_ID)
  expect(loadEditQuotaMock).toHaveBeenCalledExactlyOnceWith()
}

// Every lookup is anchored inside the chat panel, and the panel is awaited first. Two jobs, both
// load-bearing: nothing can pass vacuously against a route still in its loading state, and a
// same-named control elsewhere in the page chrome cannot stand in for the chat panel's own.
async function chatPanel() {
  return await screen.findByTestId(AI_CHAT_PANEL)
}

describe('DocumentEditorPage — an account over its daily edit quota', () => {
  beforeEach(() => {
    loadEditorDocumentMock.mockReset()
    loadEditQuotaMock.mockReset()
  })

  it('disables the chat input and the send control', async () => {
    renderEditorFor(OVER_QUOTA)

    const panel = await chatPanel()
    // Both halves of "cannot type an instruction". A disabled input beside a live send control
    // still submits — whatever the composer already held, or an empty instruction — and the
    // scenario would read as satisfied while the user is not actually stopped.
    expect(await within(panel).findByTestId(MESSAGE_INPUT)).toBeDisabled()
    expect(within(panel).getByTestId(SEND_BUTTON)).toBeDisabled()

    expectBothLoadsIssuedExactlyOnce()
  })

  it('shows the reset hint carrying the instant the API returned, verbatim', async () => {
    renderEditorFor(OVER_QUOTA)

    const panel = await chatPanel()
    const hint = await within(panel).findByTestId(QUOTA_RESET_HINT)
    // Visible, not merely mounted — the Selenium layer asserts `hint.is_displayed()` and this is
    // the jsdom equivalent. A hint rendered behind `display:none` (collapsed panel section, a
    // `hidden` attribute left on) satisfies `findByTestId` and still tells the user nothing about
    // why their composer is dead.
    expect(hint).toBeVisible()
    expect(hint).toHaveAttribute('data-resets-at', RESETS_AT_WIRE)

    // The lead is its own element because the sentence the mockup renders
    // (`mockups/desktop/06-over-quota.html`) ends in a wall-clock countdown — "через 6 ч 12 мин"
    // — that no literal can pin. Splitting the invariant half out is what lets this stay an
    // exact-equality assertion instead of decaying into a prefix match.
    expect(within(hint).getByTestId(QUOTA_RESET_HINT_LEAD).textContent?.trim()).toBe(
      EXPECTED_RESET_HINT_LEAD,
    )

    expectBothLoadsIssuedExactlyOnce()
  })

  it('leaves the revisions control usable', async () => {
    renderEditorFor(OVER_QUOTA)

    const panel = await chatPanel()
    // Asserted enabled BEFORE the click: the regression this spec line forbids is an over-quota
    // branch that disables the whole panel, composer and revisions control alike.
    const toggle = await within(panel).findByTestId(REVISIONS_TOGGLE)
    expect(toggle).toBeEnabled()
    expect(within(panel).queryByTestId(REVISIONS_PANEL)).toBeNull()

    fireEvent.click(toggle)

    // Ordered after the closed-state check above, so this cannot pass against a panel that was
    // simply always open — the toggle must be the thing that opened it. `toBeVisible`, not
    // `toBeInTheDocument`: the latter is already guaranteed by `findByTestId` (which throws when
    // the node is missing), so it asserted nothing the line above it had not — while a panel
    // mounted with `display:none` is not a panel that opened. Mirrors the Selenium layer's
    // `panel.is_displayed()`.
    expect(await within(panel).findByTestId(REVISIONS_PANEL)).toBeVisible()

    expectBothLoadsIssuedExactlyOnce()
  })

  it('leaves the input and the send control live for an account within its quota', async () => {
    renderEditorFor(WITHIN_QUOTA)

    const panel = await chatPanel()
    // The counter-case the acceptance test structurally cannot write. Without it, a composer
    // disabled unconditionally — or one with no quota read at all behind it — is green.
    expect(await within(panel).findByTestId(MESSAGE_INPUT)).toBeEnabled()
    expect(within(panel).getByTestId(SEND_BUTTON)).toBeEnabled()

    // Absence, not "hidden": a rendered-but-invisible hint still carries a claim about the
    // account's quota that is false here.
    expect(within(panel).queryByTestId(QUOTA_RESET_HINT)).toBeNull()
    expectBothLoadsIssuedExactlyOnce()
  })
})
