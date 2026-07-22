import { StrictMode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'

// Scenario 3.2 — the exchange is issued EXACTLY ONCE per handoff code even when the callback's
// effect runs twice. `StrictMode` is the real-world double-run: React dev mounts, tears down and
// remounts every component, replaying effects. The handoff code is single-use, so a second POST
// would be a replay the server must reject — the user would see an error after a valid sign-in.
//
// Asserted in BOTH directions, deliberately:
//   at-MOST-once  — exactly one `oauthExchange` call for the one code.
//   at-LEAST-once  — the sign-in actually COMPLETES: saveSession + navigate still happen.
// The second direction is not redundant. A once-guard that suppresses the duplicate by also
// disarming the surviving run degrades into a permanent spinner — zero exchanges resolved into
// zero stores — and a test that only counted "<= 1 call" would score that regression as a PASS.
//
// Seams mirror OAuthCallback.success.test.tsx exactly (exchange api, saveSession, useNavigate;
// safeRedirectTarget left REAL so the landing target is the in-app default '/').

const CODE = 'handoff-once-42'
const SESSION = {
  accessToken: 'acc-once-1',
  refreshToken: 'ref-once-1',
  accessTokenExpiresAt: '2026-07-22T10:00:00Z',
  refreshTokenExpiresAt: '2026-07-29T10:00:00Z',
}

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../../api/oauthExchangeApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/oauthExchangeApi')>()
  return { ...actual, oauthExchange: vi.fn() }
})

vi.mock('../../utils/authSession', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../utils/authSession')>()
  return { ...actual, saveSession: vi.fn() }
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

function renderUnderDoubleMount() {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={[`/auth/callback?code=${CODE}&provider=vk`]}>
        <OAuthCallback />
      </MemoryRouter>
    </StrictMode>,
  )
}

describe('OAuthCallback exactly-once exchange', () => {
  // Without this the first test's call counts leak into the second (no global clearMocks here) —
  // the same reset pattern OAuthCallback.success.test.tsx uses.
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
  })

  // RED: under StrictMode the surviving effect run is disarmed by the first run's cleanup, so the
  // resolved exchange stores and navigates NOTHING — the screen hangs on the spinner.
  // Actual failure: AssertionError: expected "vi.fn()" to be called 1 times, but got 0 times
  // (line 96, saveSession) — the exchange DID fire exactly once, but nothing was stored.
  // Skipped so the suite stays green between red and green; green-frontend un-skips.
  it.skip('issues one exchange under a double mount AND still completes the sign-in', async () => {
    const exchange = deferred<typeof SESSION>()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(exchange.promise)
    vi.mocked(authSession.saveSession).mockReturnValue(true)

    renderUnderDoubleMount()

    // at-MOST-once: the effect ran twice, but the single-use code was spent on ONE request.
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: CODE })

    await act(async () => {
      exchange.resolve(SESSION)
      await exchange.promise
    })

    // at-LEAST-once: the surviving run carried the result all the way through. A guard that
    // silenced the duplicate by cancelling the winner leaves these at 0 and fails here.
    expect(authSession.saveSession).toHaveBeenCalledTimes(1)
    expect(authSession.saveSession).toHaveBeenCalledWith({
      accessToken: SESSION.accessToken,
      refreshToken: SESSION.refreshToken,
    })
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
    // ...and the transient spinner is gone from the caller's point of view: the sign-in resolved
    // rather than hanging. (Route swap is the router's job; here the state is simply not "failed".)
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
    expect(screen.getByTestId('oauth-callback-loading')).toHaveAttribute(
      'class',
      'auth-card oauth-callback-card',
    )
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Завершаем вход…')
  })

  // Carried from the 3.1 align-design review: the callback's whole visual shell rests on one
  // `import './AuthForm.css'` plus these two shared classnames. jsdom applies no CSS, so if an
  // import tidy-up or a classname rename drops the shell to a naked box, NOTHING else goes RED.
  // This pins the class contract itself. Born-green — 3.1 align-design already ships it.
  it('keeps the shared auth shell classes on the loading state', () => {
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(deferred<typeof SESSION>().promise)

    renderUnderDoubleMount()

    expect(screen.getByTestId('oauth-callback-loading')).toHaveAttribute(
      'class',
      'auth-card oauth-callback-card',
    )
    const subtitle = screen.getByText('Это займёт пару секунд. Не закрывайте страницу.')
    expect(subtitle).toHaveAttribute('class', 'auth-subtitle oauth-callback-subtitle')
    expect(subtitle.tagName).toBe('P')
  })
})
