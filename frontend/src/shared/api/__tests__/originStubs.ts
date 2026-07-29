// The transport-level fixture shared by every suite that drives the REAL `fetch` → `httpClient`
// → `send` chain against a refusing origin. Lives beside `originErrorBodies.ts` because the body
// and the stub that serves it are one fixture: four suites were hand-rolling a byte-identical
// `vi.stubGlobal('fetch', vi.fn(() => new Response(JSON.stringify(body), { status: 500 })))`, and
// a fixture copied four times is a fixture that drifts in three of them.
import { vi, type Mock } from 'vitest'
import { clearSession, saveSession } from '../../../features/auth/utils/authSession'

// One definition of the seeded session, so the `Authorization` header a suite ASSERTS is the same
// literal the session was SEEDED with — a drifting copy makes the header assertion vacuous.
export const ACCESS_TOKEN = 'access-1'
export const REFRESH_TOKEN = 'refresh-1'

// Typed with the arguments `httpClient` actually passes, so recorded calls destructure as a
// `[url, init]` tuple without a cast and a drift in the transport's call shape is a tsc error
// rather than an `undefined` that quietly makes a request assertion pass.
export type FetchMock = Mock<(input: string, init: RequestInit) => Promise<Response>>

// Every call under test goes through `authorizedRequest`: without a token the request never
// reaches the transport and the 5xx under test is unreachable.
export function seedSession(): void {
  saveSession({ accessToken: ACCESS_TOKEN, refreshToken: REFRESH_TOKEN })
}

export function resetSession(): void {
  clearSession()
  vi.unstubAllGlobals()
}

// A REAL `Response`, not a duck-typed literal: `performRequest` reads `res.headers`
// (httpClient.ts:144), and a stub without it only survives on the `headers?.get` optional chain —
// i.e. the fixture would stand in for a contract it does not implement.
export function originResponse(body: Record<string, unknown>, status: number): Response {
  return new Response(JSON.stringify(body), { status })
}

// Installs the stub AND hands back the mock, so a suite can assert what actually went out. A stub
// whose recorded calls are never read cannot tell "the origin refused" from "the request was
// never sent" — both reach the same catch and read identically at the hook's `error`.
export function stubOriginError(body: Record<string, unknown>, status = 500): FetchMock {
  const fetchMock: FetchMock = vi.fn(() => Promise.resolve(originResponse(body, status)))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// `METHOD /path` per call, in order. `send` omits `method` for a GET, so the default is spelled
// out here rather than leaking `undefined` into every expected log.
export function requestLog(fetchMock: FetchMock): string[] {
  return fetchMock.mock.calls.map(([input, init]) => `${init.method ?? 'GET'} ${input}`)
}

export function authorizationHeaders(fetchMock: FetchMock): string[] {
  return fetchMock.mock.calls.map(
    ([, init]) => (init.headers as Record<string, string>).Authorization,
  )
}
