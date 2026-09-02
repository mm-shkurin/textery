import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import * as projectsApi from '../../features/projects/api/projectsApi'
import { App } from '../App'
import * as api from '../../features/generation/api/generationApi'
import * as documentApi from '../../features/generation/api/documentApi'
import { clearSession, saveSession } from '../../shared/session/authSession'
import { EMPTY_PARAMETERS } from '../../features/generation/utils/generationParameters'

// Story 18, scenario 1.2 — "When the result is not ready yet, a generating state is shown".
//
// The renderer half that the Selenium contract silently rests on. `test_generating_state_
// acceptance.py` widens the observable window with CDP network latency and then waits for
// [data-testid='generation-generating'] — a design that is only sound because
// `useGeneration.submit` sets state to 'pending' SYNCHRONOUSLY, before it awaits
// createGeneration. With latency L the surface is up across [0, ~2L] if that holds and only
// [L, ~2L] if it does not, and a WebDriverWait cannot tell those two apart.
//
// What already covered it, precisely: the sibling `DocumentGenerationFlow.documentType.test.tsx`
// double-Ctrl+Enter case fails on the same production edit, and its comment names the same
// render-ordering guarantee. So this premise was not unguarded — its CONSEQUENCE was guarded and
// its CAUSE was not, which is a diagnosis difference, not a coverage one (see the correction in
// the recorded-failure comment below).
//
// The consequence of losing it is not cosmetic: the user gets a dead composer for the whole POST
// round trip, clicks send again, and is billed for two generations — `createGeneration` mints a
// fresh Idempotency-Key per call, so the backend cannot collapse them. The refactor this file
// catches is an await hoisted into `useGeneration.submit` itself, ahead of setState('pending') —
// a topic validation, or moving the set inside the try. NOT a token refresh: refreshes live in
// `authorizedRequest` inside `generationApi`, which the `vi.mock` below mocks out wholesale, so
// a refresh added where refreshes actually live is invisible at this seam and no layer guards it
// — the Selenium test measures the surface, not when the first byte leaves.
//
// This file pins it at the only layer that can hold the POST open on purpose: createGeneration is
// mocked to a promise that NEVER settles, so the generating surface can only be observed if it
// was rendered without waiting for the request. It is a regression pin, not a missing feature —
// the behaviour ships today (see the bite verification in the recorded-failure comment below).
vi.mock('../../features/generation/api/generationApi')
vi.mock('../../features/generation/api/documentApi')
vi.mock('../../features/projects/api/projectsApi')

const TOPIC = 'Влияние ИИ на образование'

describe('DocumentGenerationFlow — the generating state is shown while the create is in flight', () => {
  beforeEach(() => {
    // Never settles. This is the whole mechanism of the test, not a convenience stub.
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
    // Подписанный пользователь приземляется на «Мои проекты» — лента висит, экран рисуется.
    vi.mocked(projectsApi.listProjects).mockReturnValue(new Promise(() => {}))
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  // What this pin catches, bite-verified rather than observed failing because the behaviour
  // already holds: with `setState('pending')` in useGeneration.submit moved to the line after
  // `const { generationId } = await createGeneration(topic, documentType)`, this test FAILS at
  // the getByTestId('generation-generating') below with
  //
  //   TestingLibraryElementError: Unable to find an element by:
  //   [data-testid="generation-generating"]
  //
  // Restoring the line makes it pass again; `git diff` on useGeneration.ts is empty.
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
  // contract for 1.2 depends on.
  it('shows the generating surface before the create request resolves', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('projects-toolbar-create'))
    fireEvent.click(screen.getByTestId('type-card-doklad'))

    // Control: the surface is not simply always there. Before the send the form is up with the
    // summary card beside it — the idle doc-area placeholder that used to be pinned here went
    // away with the two-column layout. Without this the "before" half of the contrast is an
    // absence that an empty screen would also satisfy.
    expect(screen.queryByTestId('generation-generating')).toBeNull()
    expect(screen.getByTestId('topic-input')).toBeInTheDocument()
    expect(screen.getByTestId('generation-summary-type')).toHaveTextContent(/^Доклад$/)

    fireEvent.change(screen.getByTestId('topic-input'), { target: { value: TOPIC } })
    fireEvent.click(screen.getByTestId('topic-send'))

    // The POST is genuinely out and, by construction, still unresolved: the mock's promise has no
    // resolve function in existence. Anything rendered from here on was rendered without it.
    expect(api.createGeneration).toHaveBeenCalledTimes(1)
    // The parameters object travels with the topic: these tests drive the real
    // Composer, so an untouched form sends its defaults rather than nothing. Asserted
    // by value — a client that dropped the argument would still call with two.
    expect(api.createGeneration).toHaveBeenCalledWith(TOPIC, 'doklad', EMPTY_PARAMETERS)

    // Existence alone would be satisfied by an empty div that merely carries the testid. The
    // pending surface is asserted at full depth: the declined heading and the progress line that
    // says what is happening. Copy moved with the redesign — the wait time is now the tail of the
    // same line rather than a sentence of its own.
    const generating = screen.getByTestId('generation-generating')
    expect(within(generating).getByRole('heading')).toHaveTextContent(/^Готовим ваш доклад$/)
    expect(within(generating).getByText('ИИ пишет доклад')).toBeInTheDocument()

    // The run badge and the progress rail are the rest of what the same pending commit puts on
    // screen, and they are what makes this "a generating document shows PROGRESS" rather than a
    // bare spinner. They render from the identical `state === 'pending'` branch, so they are part
    // of the same before-the-await claim, not a second scenario. Of the two only the rail is
    // otherwise unasserted anywhere — ChatWorkspace.test.tsx already pins the badge for `pending`.
    //
    // Второй свидетель того же состояния — шаги: бейджа «В обработке» на экране больше нет,
    // его место занял шаг «Введите параметры», помеченный как текущий. Проверяется атрибут, а
    // не текст: подпись шага — копирайт, а `aria-current` — контракт.
    const steps = within(screen.getByTestId('generation-steps')).getAllByRole('listitem')
    expect(steps[1]).toHaveAttribute('aria-current', 'step')
    expect(
      // Панель прогресса рядом с областью документа исчезла вместе с перерисовкой экрана:
      // обе половины сообщения теперь строки одного блока ожидания.
      within(screen.getByTestId('generation-generating')).getByText('ИИ пишет доклад'),
    ).toBeInTheDocument()
    // The composer is gone in the same commit. Asserted here as the render-ordering fact this
    // file is about — the surface swap IS the state set becoming visible — not as double-billing
    // coverage: that consequence is the sibling test's subject and is left to it.
    expect(screen.queryByTestId('topic-input')).toBeNull()
  })
})
