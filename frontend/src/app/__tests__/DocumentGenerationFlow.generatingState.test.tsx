import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import App from '../App'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { clearSession, saveSession } from '../../features/auth/utils/authSession'

// Story 18, scenario 1.2 — "When the result is not ready yet, a generating state is shown".
//
// The renderer half that the Selenium contract silently rests on. `test_generating_state_
// acceptance.py` widens the observable window with CDP network latency and then waits for
// [data-testid='generation-generating'] — a design that is only sound because
// `useGeneration.submit` sets state to 'pending' SYNCHRONOUSLY, before it awaits
// createGeneration. With latency L the surface is up across [0, ~2L] if that holds and only
// [L, ~2L] if it does not, and a WebDriverWait cannot tell those two apart. Nothing asserts it.
//
// The consequence of losing it is not cosmetic: the user gets a dead composer for the whole POST
// round trip, clicks send again, and is billed for two generations — `createGeneration` mints a
// fresh Idempotency-Key per call, so the backend cannot collapse them. Any refactor that puts an
// await ahead of setState('pending') (topic validation, a token refresh, moving the set inside
// the try) does that, while the Selenium test stays green.
//
// This file pins it at the only layer that can hold the POST open on purpose: createGeneration is
// mocked to a promise that NEVER settles, so the generating surface can only be observed if it
// was rendered without waiting for the request. It is a regression pin, not a missing feature —
// the behaviour ships today (see the bite verification in the recorded-failure comment below).
vi.mock('../../features/generation/api/generationApi')
vi.mock('../../features/generation/api/documentApi')

const TOPIC = 'Влияние ИИ на образование'

describe('DocumentGenerationFlow — the generating state is shown while the create is in flight', () => {
  beforeEach(() => {
    // Never settles. This is the whole mechanism of the test, not a convenience stub.
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  // RED, recorded failure. The behaviour already holds, so this was bite-verified instead of
  // observed failing: with `setState('pending')` in useGeneration.submit moved to the line after
  // `const { generationId } = await createGeneration(topic, documentType)`, this test FAILS at
  // the getByTestId('generation-generating') below with
  //
  //   TestingLibraryElementError: Unable to find an element by:
  //   [data-testid="generation-generating"]
  //
  // Restoring the line makes it pass again; `git diff` on useGeneration.ts is empty.
  //
  // The exact texts asserted below were verified green by running this file once with the marker
  // off — a skipped test compiles but never executes, so an expected string that does not match
  // DocArea would otherwise sit here undetected until green-frontend unskips it.
  //
  // Correction to the premise this file was written on, found by running that break against the
  // WHOLE suite rather than this file alone: the regression is NOT silent everywhere. The sibling
  // `DocumentGenerationFlow.documentType.test.tsx` "bills one generation for a double Ctrl+Enter"
  // case fails too (2 failed / 538 passed), because it stubs createGeneration the same
  // never-settling way and the still-mounted Composer accepts the second keydown. So the
  // double-billing CONSEQUENCE already had a guard. What had none is the CAUSE, and the
  // difference matters for diagnosis: that test fails with "expected 1 call, got 2", which points
  // an engineer at Composer's missing in-flight guard — the wrong file. This one fails on the
  // missing surface, which is both the actual defect and the exact assertion the Selenium
  // contract for 1.2 depends on. green-frontend removes this marker only.
  it.skip('shows the generating surface before the create request resolves', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))

    // Control: the surface is not simply always there. Before the send the composer is up and the
    // doc area is on its idle placeholder, which carries no testid at all — so it is pinned by the
    // heading only the idle branch of DocArea renders. Without this the "before" half of the
    // contrast is an absence that an empty doc area would also satisfy.
    expect(screen.queryByTestId('generation-generating')).toBeNull()
    expect(screen.getByTestId('topic-input')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Опишите тему доклада' })).toBeInTheDocument()

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: TOPIC } })
    fireEvent.click(screen.getByTestId('topic-send'))

    // The POST is genuinely out and, by construction, still unresolved: the mock's promise has no
    // resolve function in existence. Anything rendered from here on was rendered without it.
    expect(api.createGeneration).toHaveBeenCalledTimes(1)
    expect(api.createGeneration).toHaveBeenCalledWith(TOPIC, 'doklad')

    // Existence alone would be satisfied by an empty div that merely carries the testid. The
    // pending surface is fully determined by DocArea's pending branch, so it is asserted at that
    // depth: a spinner heading and the wait-time line, both exact and anchored.
    const generating = screen.getByTestId('generation-generating')
    expect(within(generating).getByRole('heading')).toHaveTextContent(/^Готовим ваш доклад$/)
    expect(
      within(generating).getByText('Обычно занимает 1–2 минуты — страница обновится автоматически'),
    ).toBeInTheDocument()

    // The run badge and the progress rail are the rest of what the same pending commit puts on
    // screen, and they are what makes this "a generating document shows PROGRESS" rather than a
    // bare spinner. They render from the identical `state === 'pending'` branch, so they are part
    // of the same before-the-await claim, not a second scenario.
    expect(screen.getByText('В обработке')).toBeInTheDocument()
    expect(screen.getByText('ИИ пишет доклад')).toBeInTheDocument()
    // The composer is gone in the same commit — that swap is what makes a second send impossible
    // during the in-flight window, and it is the other half of the double-billing protection.
    expect(screen.queryByTestId('topic-input')).toBeNull()
  })
})
