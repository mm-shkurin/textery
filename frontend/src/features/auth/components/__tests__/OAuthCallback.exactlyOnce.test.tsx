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

  // Under StrictMode the surviving effect run must NOT be disarmed by the first run's cleanup: a
  // shared mountedRef is re-armed on remount, so the resolved exchange stores and navigates.
  it('issues one exchange under a double mount AND still completes the sign-in', async () => {
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
    // ...and it resolved rather than failing. `navigate` is mocked, so the route never swaps and
    // the component legitimately stays on the loading branch — the positive check is that this is
    // the loading state and NOT the terminal error state.
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
    expect(screen.getByTestId('oauth-callback-loading')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Завершаем вход…')
  })

  // Born-green guard (premortem CREDIBLE from red 3.2 review): the mountedRef fix must serve the
  // ERROR branch too, not just success. Under the same double mount, a REJECTED exchange must
  // still render the terminal error — a success-path-only fix would leave `.catch` gated on a
  // disarmed flag and hang the spinner forever.
  it('renders the error state under a double mount when the exchange rejects', async () => {
    // A BUSINESS-shaped rejection (carries an errorCode, no 5xx status) — so scenario 4.2's
    // `isLoginNetworkError` branch classifies it as terminal, not a transport failure. A bare
    // Error here would now be a network failure and route to /login (4.2), which is a different
    // scenario; this test only means to prove the `.catch` survives StrictMode's double mount and
    // reaches the terminal error card.
    const rejection = Promise.reject<typeof SESSION>({
      errorCode: 'INVALID_OR_EXPIRED_OAUTH_CODE',
      message: 'expired',
    })
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(rejection)
    // Swallow the terminal rejection so it is not flagged as unhandled once the component's
    // `.catch` has consumed it.
    const settled = rejection.catch(() => undefined)

    renderUnderDoubleMount()

    await act(async () => {
      await settled
    })

    expect(await screen.findByTestId('oauth-callback-error')).toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
  })

  // Born-green guard (premortem CREDIBLE): the mountedRef fix must also serve the fail-closed
  // saveSession-false branch under double mount — a refused store shows the terminal error rather
  // than hanging on the spinner.
  it('renders the error state under a double mount when the session store is refused', async () => {
    const exchange = deferred<typeof SESSION>()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(exchange.promise)
    vi.mocked(authSession.saveSession).mockReturnValue(false)

    renderUnderDoubleMount()

    await act(async () => {
      exchange.resolve(SESSION)
      await exchange.promise
    })

    expect(await screen.findByTestId('oauth-callback-error')).toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
    expect(authSession.saveSession).toHaveBeenCalledTimes(1)
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
