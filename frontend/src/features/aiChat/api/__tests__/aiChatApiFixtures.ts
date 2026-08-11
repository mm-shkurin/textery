// Test-support for the aiChat API-client tests — `editorDocumentApi.test.ts` and
// `editQuotaApi.test.ts`: the fetch stub, the assertion helpers, and the wire fixtures. Split out
// on the 200-line limit, along the seam that costs nothing — each test file keeps all of its cases
// and its own describe marker, and what moved here is the machinery none of them narrate.
//
// Named for the FEATURE's api layer, not for `editorDocumentApi`: it was named after its first
// consumer, and once `editQuotaApi.test.ts` began importing `stubFetch`, `okJson`, `QUOTA_URL` and
// the 401 pair from it, that name claimed a document-scoped ownership the contents contradict —
// `QUOTA_URL` is precisely the account-scoped path the quota module exists to keep separate.
// Scoped to `api/__tests__/` and not to the feature root: the cross-layer constants both the api
// and the component tests assert against live in `aiChat/__tests__/editQuotaWireFixtures.ts`, and
// keeping this file api-only is what stops a component test from importing a fetch stub.
//
// Mirrors `auth/api/__tests__/loginApiTestUtils.ts`. As there, no `vi.mock` lives here: module
// mocks are hoisted and file-scoped and must stay in the test file.
import { afterEach, beforeEach, expect, vi } from 'vitest'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Setup, not subject: every case in both files goes through `send` -> `authorizedRequest`, which
// throws SessionExpiredError BEFORE fetch is reached when no token is stored — so without a stored
// session no case would exercise the mapping it is about.
//
// The teardown half is why this lives here rather than being re-typed per file: `stubFetch` below
// installs a global via `vi.stubGlobal` and does not remove it, so `vi.unstubAllGlobals()` is that
// fixture's own teardown and belongs beside it. Left to each consumer to remember, a file that
// forgot would leak a dead fetch stub into every test that ran after it.
//
// Registers hooks, hence the name — call it in the describe body, not at module scope. The stored
// access token is 'access-1'; the `Authorization: 'Bearer access-1'` assertions stay spelled out
// literally at their call sites, where an expected value should be readable without a lookup.
export function signedInSessionAroundEach(): void {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })
}

// The default implementation THROWS rather than returning undefined. An unstubbed extra call would
// otherwise resolve to `undefined` and blow up inside httpClient on `res.ok`, turning "the client
// made a request this test never authorised" into an unreadable TypeError. Each test also pins the
// exact call list, so an extra call is a failure and not a shrug.
export function stubFetch(...responses: unknown[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn()
  fetchMock.mockImplementation(() => {
    throw new Error('fetch called more times than the test stubbed')
  })
  responses.forEach((response) => fetchMock.mockResolvedValueOnce(response))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// The URLs the client actually requested, in call order — the actual half of every "no renew, no
// replay" and "renew and replay" assertion in both api test files. Named rather than re-spelled as
// `mock.calls.map(([url]) => url)` at each of its six call sites: the destructure is transport
// mechanics, while what the cases are claiming is the SEQUENCE of endpoints, and a list compared
// with toEqual is what pins both its contents and its length.
export function requestedUrls(fetchMock: ReturnType<typeof vi.fn>): unknown[] {
  return fetchMock.mock.calls.map((call: unknown[]) => call[0])
}

// The three claims every refusal case makes about the thrown value, in one place because they only
// mean something together: the CLASS is what `useEditorDocument` branches on, the `name` is what
// survives a green that re-declares the class in a second module (two structurally identical
// classes, one `instanceof` that silently goes false), and the MESSAGE is what separates a raised
// class from an implementation that merely echoes `body.message`. Dropping any one of the three
// re-opens a green that the other two let through — so they travel together.
export function expectErrorIdentity(
  error: unknown,
  type: new (...args: never[]) => Error,
  name: string,
  message: string,
): void {
  expect(error).toBeInstanceOf(type)
  expect((error as Error).name).toBe(name)
  expect((error as Error).message).toBe(message)
}

// A 200 carrying `body`. Shared rather than re-declared per test file: the shape is pure transport
// machinery no case narrates, and a local copy in each file is a second place for the `ok`/`status`
// pair to drift out of agreement with what httpClient actually branches on (`res.ok`).
export function okJson(body: unknown): { ok: true; status: 200; json: () => Promise<unknown> } {
  return { ok: true, status: 200, json: async () => body }
}

// VITE_API_BASE_URL is empty (frontend/.env), so httpClient's API_BASE is '' and the fetched URL is
// the path verbatim. Asserted with toBe, not toContain: `toContain` passes for
// '/api/v1/documents/doc-1/versions' and for a doubled base, which are different endpoints.
export const DOCUMENT_URL = '/api/v1/documents/doc-1'
export const REFRESH_URL = '/api/v1/auth/refresh'
// Account-scoped, NOT '/api/v1/documents/{id}/ai-edits/quota'. Lives here beside its peers so the
// endpoint table has one home rather than two.
export const QUOTA_URL = '/api/v1/ai-edits/quota'

// The 401 both API test files drive their renew-and-replay case with. Stubbed twice per case: the
// first is the original request, the second is the refresh, whose failure is the only path that
// reaches a caller as SessionExpiredError.
export const UNAUTHORIZED_RESPONSE = {
  ok: false,
  status: 401,
  json: async () => ({ error_code: 'UNAUTHORIZED', message: 'Unauthorized' }),
}
export const SESSION_EXPIRED_MESSAGE = 'Сессия истекла. Войдите снова.'

// The wire text is deliberately NOT the Russian sentence the error carries. DocumentNotFoundError
// is constructed with no arguments and owns its message, so asserting the Russian constant while
// the body says something else proves the class was raised — where matching bodies would also pass
// for an implementation that merely echoes `body.message` into a plain Error.
export const NOT_FOUND_RESPONSE = {
  ok: false,
  status: 404,
  json: async () => ({ error_code: 'NOT_FOUND', message: 'Document not found' }),
}
export const NOT_FOUND_MESSAGE = 'Документ не найден'

// The 500 both api test files drive their "everything else stays a described generic failure" case
// with. Unlike the 404 pair above, the asserted MESSAGE here is the body's own text — `send`
// flattens a non-401/409 refusal by echoing `message` through `describeFailure` — so the response
// and the expectation are two halves of one claim and must not drift apart. Two hand-kept copies
// were exactly two places for them to drift, in a case whose whole point is that the SERVER's
// sentence survives rather than being replaced by a raised class's fixed one.
export const INTERNAL_ERROR_RESPONSE = {
  ok: false,
  status: 500,
  json: async () => ({ error_code: 'INTERNAL_ERROR', message: 'Внутренняя ошибка' }),
}
export const INTERNAL_ERROR_MESSAGE = 'Внутренняя ошибка'
