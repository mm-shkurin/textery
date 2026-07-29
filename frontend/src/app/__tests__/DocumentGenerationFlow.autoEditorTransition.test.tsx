import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import App from '../App'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { clearSession, saveSession } from '../../features/auth/utils/authSession'

// Story 18, scenario 2.1 — "When the text becomes ready, the surface becomes the editor, and the
// user made no extra click to get there".
//
// SEAM: the renderer/hook join, driven through the real UI with both api modules mocked — the
// established pattern of the two siblings in this directory. Chosen deliberately over the two
// alternatives this lane has been burned by before:
//
//   * renderHook on useGeneration / useFlowNavigation would pin hook STATE, and hook state is not
//     where the defect is. `runPollAttempt` already sets state 'completed' correctly today; what
//     is missing is that nothing turns that state into the editor. A hook-level assertion could go
//     green with the surface still read-only — verbatim the "pins a contract one layer below where
//     the defect lives" mistake recorded against 1.1's red-frontend-api.
//   * generationApi / documentApi is red-frontend-api's seam and owns the from-generation wire
//     contract; it cannot see a surface at all.
//
// The transition is a RENDER decision spanning three files, and only a render can observe it:
// `useGeneration.runPollAttempt` handles `completed` by setting content + state and nothing else;
// `DocArea` renders `completed` as a read-only `doc-body`; `DocumentGenerationFlow` mounts
// ManualEditor only for `mode === 'manual'`, which `selectType` never sets on the create path.
//
// GENUINE RED — the transition does not exist. Unlike every step of scenario 1.2, this is not a
// coverage pin on shipped behaviour, and no bite verification stands in for a real failure: the
// failure below was observed live before the marker went on.
vi.mock('../../features/generation/api/generationApi')
vi.mock('../../features/generation/api/documentApi')

const TOPIC = 'Влияние ИИ на образование'
const GENERATION_ID = 'gen-2-1'
const GENERATED_TEXT = 'Готовый текст доклада'

describe('DocumentGenerationFlow — a completed generation opens itself in the editor', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockResolvedValue({
      generationId: GENERATION_ID,
      status: 'pending',
    })
    // The first poll — `useGeneration.submit` fires one immediately — already observes completion,
    // so the whole scenario resolves inside this render with no timer advanced. The generating
    // state is 1.2's subject and is deliberately not re-pinned here.
    vi.mocked(api.getGeneration).mockResolvedValue({
      generationId: GENERATION_ID,
      status: 'completed',
      content: GENERATED_TEXT,
      topic: TOPIC,
      volumePages: 5,
      documentType: 'доклад',
      createdAt: '2026-07-29T10:00:00Z',
    })
    // Never settles: whatever green does about persisting the converted document, this test must
    // not depend on it resolving. The claim under test is that the EDITOR SURFACE arrives by
    // itself — not what the document endpoint says afterwards.
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.getDocument).mockReturnValue(new Promise(() => {}))
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  // RED, observed live 2026-07-29 (1 failed / 0 passed), at the `findByTestId` call below:
  //
  //   TestingLibraryElementError: Unable to find an element by: [data-testid="manual-editor"]
  //
  // The printed DOM is the diagnosis in full: `<div class="doc-body markdown-body"
  // data-testid="doc-body"><p>Готовый текст доклада</p></div>` beside a `Создать новый доклад`
  // button. The generation completed, the text arrived, and the surface stayed read-only — there
  // is no code path from `state === 'completed'` to the editor. Green removes this marker.
  it.skip('replaces the read-only result with the editor without a further gesture', async () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))
    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: TOPIC } })

    // The LAST user gesture in this test. Every assertion below runs against a page nobody
    // touched again — that is the "no extra click" half of the scenario, and it is load-bearing:
    // a green that adds an "Открыть в редакторе" button satisfies the surface assertion only if
    // this file is edited, which is what makes the absence of a further fireEvent an assertion
    // rather than an omission.
    fireEvent.click(screen.getByTestId('topic-send'))

    expect(api.createGeneration).toHaveBeenCalledTimes(1)
    expect(api.createGeneration).toHaveBeenCalledWith(TOPIC, 'doklad')

    // The editor shell is lazy (Tiptap), so this await covers a real chunk load, not just a state
    // flush. `findByTestId` is the only wait in the test.
    const editor = await screen.findByTestId('manual-editor')

    // Deliberately NOT `expect(editor).toBeInTheDocument()` — `findByTestId` already throws when
    // the node is absent, so that line asserts nothing `await` has not already asserted, and the
    // pair together are satisfied by an empty `<div data-testid="manual-editor" />`. What makes
    // the surface an EDITOR rather than the completed view wearing the editor's name is that it
    // accepts typing without a further action: `contenteditable` by equality, not truthiness.
    // This is the renderer-side twin of the same fix the 2.1 Selenium contract took.
    const contentArea = within(editor).getByTestId('editor-content-area')
    expect(contentArea).toHaveAttribute('contenteditable', 'true')

    // The editor must open for the type the user picked, and the breadcrumb is where it says so.
    // Pinned by equality to the same constant the Selenium contract fixed
    // (`EXPECTED_AUTO_EDITOR_BREADCRUMB = "Доклад"`), which makes this the cheap layer that
    // catches what green owes in `ManualEditorBreadcrumb.tsx`: today those chips render
    // `Доклад · Ручной режим`, and both the hardcoded `Ручной режим` chip and the
    // `me-breadcrumb-sep` between them must go — story 18 deleted the mode modal, so that chip
    // can only decorate a choice the user is never offered. Failing here costs a second; failing
    // on the same string at green-selenium costs a live stack and reads as a missing transition.
    //
    // Honest about its limits: `doklad` is the only `available: true` card, so a green that
    // hardcodes the default satisfies this. That arm is owned by the sibling
    // `DocumentGenerationFlow.documentType.test.tsx` and the wire test, not by this file.
    expect(within(editor).getByTestId('editor-breadcrumb')).toHaveTextContent(/^Доклад$/)

    // The completed generation's read-only render is DocArea's `doc-body`. Asserting its absence
    // is what makes this a REPLACEMENT rather than an addition: an editor mounted while the
    // read-only copy is still on screen shows the user the same text twice, and leaves them to
    // work out which one accepts typing.
    expect(screen.queryByTestId('doc-body')).toBeNull()
    expect(screen.queryByTestId('generation-generating')).toBeNull()

    // The status check the transition ran on: asked for the run that was actually created, and
    // asked once. The first poll — fired by `submit` the instant the POST resolves — already
    // returns `completed`, so a second call means the transition re-read what it was already
    // holding, which scenario 2.3 exists to forbid. Polling the wrong id renders another run's
    // document and every assertion above still passes.
    //
    // What this CANNOT see, stated so nobody reads more into it: the 5s `POLL_INTERVAL_MS` never
    // elapses inside this test (real timers, milliseconds of wall clock), so a poll loop that
    // outlived its own result is invisible here — and so is it to the `generation-generating`
    // absence above, which the surface swap guarantees whether or not `stopPolling` ran. The
    // teardown leak belongs to the Selenium contract's `assert_the_poll_loop_stopped`, which
    // sleeps past the interval on purpose.
    expect(api.getGeneration).toHaveBeenCalledWith(GENERATION_ID)
    expect(api.getGeneration).toHaveBeenCalledTimes(1)
  })
})
